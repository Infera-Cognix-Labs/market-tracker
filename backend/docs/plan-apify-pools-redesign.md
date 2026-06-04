# Apify Actor Pools — Redesign Plan

## Problem Statement

Current architecture maps **1 binding = 1 actor** per feature. When an actor is
unpublished, errors out, or returns incomplete data, the job fails immediately.
There is no fallback mechanism. Additionally, `category_enrichment` exists as a
separate binding but is really just a fallback for category tracking — it should
be consolidated.

## Goals

1. **Pool-based dispatch**: Each feature (category, competitor, deals) manages an
   ordered pool of actors. If one fails or returns incomplete data, the next actor
   in the pool is tried automatically.
2. **Standard data contract**: All actors in a pool output to a validated standard
   contract per tracker type. Pool merge compares apples to apples.
3. **Enable/disable actors**: Each actor in a pool has an `enabled` flag for
   on/off switching without config deletion.
4. **Remove `category_enrichment`**: Folded into the category pool as a fallback
   actor. No separate binding.
5. **Generic pattern**: Same pool mechanism works for category, competitor, and
   deals — each feature just has its own pool config.

---

## Architecture

### Flow

```
dispatch_job("category")
  └─ dispatch actor[0] from pool → ApifyRun[0]
                                          ↓
Import Service: import ApifyRun[0] → adapter → Standard Contract[0]
  ↓
check null critical fields
  ├─ no nulls → normalize → snapshot → DONE
  └─ has nulls → dispatch actor[1] from pool → ApifyRun[1]
                                                  ↓
                               adapter → Standard Contract[1]
                                                  ↓
                               merge Contract[0] + Contract[1] → Contract[merged]
                                                  ↓
                               check nulls → ... repeat until clean or pool exhausted
```

### Components

```
┌─────────────────────────────────────────────────────────┐
│                     Config (YAML)                       │
│  actor_pools.category = [ActorPoolEntry, ...]           │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                    ApifyGateway                          │
│  resolve_pool(pool_code) → list[ActorPoolEntry]         │
│  start_run(binding_code, input) → ApifyRunLaunch        │
│  _apply_adapter(entry, input) → adapted input           │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                 Adapter Registry                         │
│  get_adapter(name) → ActorAdapter                       │
│  adapter.to_standard_contract(raw) → StandardContract   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              Standard Contracts (Pydantic)               │
│  CategoryProductRecord / CompetitorProductRecord / ...   │
│  has_null_critical_fields() → bool                      │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│               ResultImporterService                      │
│  _try_pool_fallback() → dispatch next, merge, check     │
│  _merge_contracts() → fill nulls from overlay           │
└─────────────────────────────────────────────────────────┘
```

---

## Config Schema

### `app-config.yaml`

```yaml
apify:
  actor_pools:
    category:
      - actor_id: "saswave/amazon-product-scraper"
        task_id: ""
        name: "Saswave Amazon Scraper"
        adapter: "saswave_category"
        build: "latest"
        memory_mbytes: 4096
        enabled: true
        priority: 1
      - actor_id: "junglee/amazon-product-scraper"
        task_id: ""
        name: "Junglee Fallback"
        adapter: "junglee_category"
        build: "latest"
        memory_mbytes: 4096
        enabled: true
        priority: 2
        input_adapter:
          field_map:
            search_url: "searchUrl"
            max_pages: "maxPages"

    competitor:
      - actor_id: "saswave/amazon-product-scraper"
        task_id: ""
        name: "Saswave Amazon Scraper"
        adapter: "saswave_competitor"
        build: "latest"
        memory_mbytes: 4096
        enabled: true
        priority: 1

    deals:
      - actor_id: "hJNp8X1wuz14Wc5wU"
        task_id: ""
        name: "Deals Scraper"
        adapter: "deals_scraper"
        build: "latest"
        memory_mbytes: 4096
        enabled: true
        priority: 1
```

### Config Model (`app/config/config.py`)

```python
class InputAdapterConfig(BaseModel):
    field_map: dict[str, str] = Field(default_factory=dict)

class ActorPoolEntryConfig(BaseModel):
    actor_id: str | None = None
    task_id: str | None = None
    name: str | None = None
    adapter: str | None = None          # registry key
    build: str | None = "latest"
    memory_mbytes: int | None = 4096
    enabled: bool = True
    priority: int = 0
    input_adapter: InputAdapterConfig | None = None
```

---

## Data Structures

### Gateway Runtime Models (`app/integrations/apify_gateway.py`)

```python
@dataclass(frozen=True)
class ActorPoolEntry:
    index: int                          # position in pool (0-based)
    actor_id: str | None
    task_id: str | None
    name: str | None
    build: str | None
    memory_mbytes: int | None
    adapter_name: str | None
    input_adapter: InputAdapterConfig | None

@dataclass(frozen=True)
class InputAdapter:
    field_map: dict[str, str]

@dataclass(frozen=True)
class ApifyBindingTarget:
    binding_code: str
    actor_name: str | None
    actor_id: str | None
    task_id: str | None
    build: str | None
    memory_mbytes: int | None

@dataclass(frozen=True)
class ApifyRunLaunch:
    provider_run_id: str
    default_dataset_id: str | None
    status: ExternalRunStatus | None
    raw_status: str | None
    started_at: Any
    finished_at: Any
    input_hash: str
    binding: ApifyBindingTarget
    run_input: dict[str, object]
    pool_actor_id: str | None = None
    pool_actor_name: str | None = None
    pool_index: int | None = None
```

### Binding Code Format

Binding code encodes pool position: `"category:0"`, `"category:1"`, `"deals:0"`.

This maintains backward compatibility with the current `start_run(binding_code, ...)` signature while carrying pool context.

---

## Standard Data Contracts (`app/models/contracts.py`)

Each tracker type defines a Pydantic model that all actors in its pool must produce.

### CategoryProductRecord

```python
class CategoryProductRecord(BaseModel):
    asin: str
    rank_position: int | None = None
    title: str | None = None
    brand: str | None = None
    product_url: str | None = None
    main_image_url: str | None = None
    price_current: float | None = None
    price_original: float | None = None
    currency: str | None = None
    coupon_text: str | None = None
    rating_value: float | None = None
    review_count: int | None = None
    variation_count: int | None = None
    availability_status: str | None = None
    buy_box_status: str | None = None
    buy_box_seller_name: str | None = None
    bsr_position: int | None = None
    deal_info: DealInfo | None = None

    def has_null_critical_fields(self) -> bool:
        return (
            self.price_current is None
            or self.rating_value is None
            or self.review_count is None
        )
```

### CompetitorProductRecord

```python
class CompetitorProductRecord(BaseModel):
    asin: str
    title: str | None = None
    brand: str | None = None
    price_current: float | None = None
    price_original: float | None = None
    currency: str | None = None
    rating_value: float | None = None
    review_count: int | None = None
    availability_status: str | None = None
    buy_box_status: str | None = None
    buy_box_seller_name: str | None = None
    variation_count: int | None = None

    def has_null_critical_fields(self) -> bool:
        return (
            self.price_current is None
            or self.rating_value is None
            or self.review_count is None
        )
```

### DealRecord

```python
class DealRecord(BaseModel):
    asin: str
    deal_info: DealInfo | None = None

    def has_null_critical_fields(self) -> bool:
        return self.deal_info is None
```

---

## Actor Adapter Interface (`app/integrations/adapters.py`)

```python
class ActorAdapter(Protocol):
    actor_id: str

    def to_standard_contract(
        self,
        raw_payload: dict[str, object],
        marketplace: str,
    ) -> CategoryProductRecord | CompetitorProductRecord | DealRecord | None:
        """Map raw actor output → standard contract.
        Return None if the item is invalid (e.g. missing ASIN)."""
        ...
```

### Example Adapters

```python
class SaswaveCategoryAdapter:
    actor_id = "saswave/amazon-product-scraper"

    def to_standard_contract(self, raw_payload, marketplace):
        asin = _coerce_asin(raw_payload.get("asin"))
        if not asin:
            return None
        return CategoryProductRecord(
            asin=asin,
            rank_position=_coerce_int(raw_payload.get("rank_position")),
            title=_coerce_string(raw_payload.get("title")),
            brand=_coerce_string(raw_payload.get("brand")) or "Unknown",
            price_current=_coerce_float(raw_payload.get("price")),
            rating_value=_coerce_float(raw_payload.get("rating")),
            review_count=_coerce_int(raw_payload.get("reviewCount")),
            # ... map remaining fields
        )

class JungleeCategoryAdapter:
    actor_id = "junglee/amazon-product-scraper"

    def to_standard_contract(self, raw_payload, marketplace):
        asin = _coerce_asin(raw_payload.get("asin"))
        if not asin:
            return None
        return CategoryProductRecord(
            asin=asin,
            title=_coerce_string(raw_payload.get("title")),
            brand=_coerce_string(raw_payload.get("brand")) or "Unknown",
            price_current=_extract_nested_price(raw_payload, "price"),
            rating_value=_coerce_float(raw_payload.get("stars")),
            review_count=_coerce_int(raw_payload.get("reviewsCount")),
            # ... map remaining fields
        )
```

### Adapter Registry (`app/integrations/adapter_registry.py`)

```python
_ADAPTER_REGISTRY: dict[str, ActorAdapter] = {
    "saswave_category": SaswaveCategoryAdapter(),
    "junglee_category": JungleeCategoryAdapter(),
    "saswave_competitor": SaswaveCompetitorAdapter(),
    "deals_scraper": DealsAdapter(),
}

def get_adapter(name: str) -> ActorAdapter:
    adapter = _ADAPTER_REGISTRY.get(name)
    if not adapter:
        raise ValueError(f"Unknown adapter: {name}")
    return adapter
```

---

## Document Changes

### JobDocument (`app/models/documents.py`)

```python
class JobDocument(WorkspaceDocument):
    # ... existing fields ...
    pool_code: str | None = None              # replaces binding_code
    current_pool_index: int = 0               # actor position in pool
```

### ApifyRunDocument

```python
class ApifyRunDocument(WorkspaceDocument):
    # ... existing fields ...
    pool_actor_id: str | None = None          # actor_id that ran
    pool_actor_name: str | None = None
    pool_index: int | None = None             # position in pool
```

### JobRunStrategy (`app/models/api.py`)

```python
class JobRunStrategy(ApiModel):
    provider: Provider
    pool_code: str | None = None              # replaces binding_code
```

---

## Service Changes

### ApifyGateway (`app/integrations/apify_gateway.py`)

New methods:

```python
def resolve_pool(self, pool_code: str) -> list[ActorPoolEntry]:
    """Load pool from config, filter enabled, sort by priority."""

def _apply_adapter(self, entry: ActorPoolEntry, run_input: dict) -> dict:
    """Transform run_input using entry's input_adapter.field_map."""

def _parse_binding(self, binding_code: str) -> tuple[str, int]:
    """Parse 'category:0' → ('category', 0)."""
```

Modified methods:

- `start_run(binding_code, ...)`: parse `"category:0"` → resolve pool → get entry at index → apply adapter → dispatch
- `resolve_binding()`: **deprecated**, kept for backward compat during migration

### RunOrchestrator (`app/services/run_orchestrator.py`)

```python
async def dispatch_job(self, workspace_id, job_code):
    # ... existing load + status check ...

    pool_code = self._resolve_pool_code(job_document.tracker_type)
    pool = self.gateway.resolve_pool(pool_code)
    first_entry = pool[0] if pool else None

    binding_code = f"{pool_code}:0"
    run_input = self._build_run_input(job_document, tracker_document)
    adapted_input = self.gateway._apply_adapter(first_entry, run_input)

    launch = await self.gateway.start_run(binding_code, adapted_input, webhooks=...)

    # ... create ApifyRunDocument with pool fields ...
    # ... update job with pool_code + current_pool_index=0 ...
```

### ResultImporterService (`app/services/result_importer_service.py`)

**Remove:**
- `_enrich_with_junglee()` (entire function)
- `_merge_record()` — replaced by `_merge_contracts()`
- `_detect_asins_with_nulls()` — replaced by contract's `has_null_critical_fields()`
- Enrichment block in `_process_job()` (lines ~320-359)

**Add:**

```python
async def _try_pool_fallback(
    self,
    job_document: JobDocument,
    current_contracts: list[CategoryProductRecord],
    current_run_document: ApifyRunDocument,
) -> list[CategoryProductRecord]:
    """Try next actors in pool until null fields are resolved or pool exhausted."""
    pool_code = job_document.pool_code
    if not pool_code:
        return current_contracts

    pool = self.gateway.resolve_pool(pool_code)
    current_index = job_document.current_pool_index or 0

    for next_index in range(current_index + 1, len(pool)):
        entry = pool[next_index]
        adapter = get_adapter(entry.adapter_name)

        binding_code = f"{pool_code}:{next_index}"
        run_input = dict(current_run_document.run_input or {})

        try:
            launch = await self.gateway.start_run(
                binding_code, run_input, webhooks=self._build_run_webhooks()
            )
        except ApifyRunStartError:
            logger.warning(
                "Pool fallback dispatch failed, trying next.",
                actor_id=entry.actor_id,
                pool_code=pool_code,
            )
            continue

        new_run = ApifyRunDocument(
            # ... from launch ...
            pool_actor_id=entry.actor_id,
            pool_actor_name=entry.name,
            pool_index=next_index,
            origin="POOL_FALLBACK",
        )
        await new_run.insert()

        job_document.current_pool_index = next_index
        await job_document.save()

        raw_items = await self._load_or_import_raw_items(
            workspace_id=job_document.workspace_id,
            job_document=job_document,
            run_document=new_run,
        )

        new_contracts = []
        for item in raw_items:
            contract = adapter.to_standard_contract(item.payload, tracker_context.marketplace)
            if contract is not None:
                new_contracts.append(contract)

        merged = _merge_contracts(current_contracts, new_contracts)

        if not any(c.has_null_critical_fields() for c in merged):
            return merged

    return current_contracts

def _merge_contracts(
    base: list[CategoryProductRecord],
    overlay: list[CategoryProductRecord],
) -> list[CategoryProductRecord]:
    """Fill null fields in base from overlay, matched by ASIN."""
    overlay_by_asin = {c.asin: c for c in overlay}
    merged = []
    for record in base:
        if record.asin in overlay_by_asin:
            o = overlay_by_asin[record.asin]
            merged.append(CategoryProductRecord(
                asin=record.asin,
                rank_position=record.rank_position or o.rank_position,
                title=record.title or o.title,
                brand=record.brand if record.brand not in (None, "Unknown") else o.brand,
                price_current=record.price_current or o.price_current,
                price_original=record.price_original or o.price_original,
                currency=record.currency or o.currency,
                coupon_text=record.coupon_text or o.coupon_text,
                rating_value=record.rating_value or o.rating_value,
                review_count=record.review_count or o.review_count,
                variation_count=record.variation_count or o.variation_count,
                availability_status=record.availability_status or o.availability_status,
                buy_box_status=record.buy_box_status or o.buy_box_status,
                buy_box_seller_name=record.buy_box_seller_name or o.buy_box_seller_name,
                bsr_position=record.bsr_position or o.bsr_position,
                deal_info=record.deal_info or o.deal_info,
                main_image_url=record.main_image_url or o.main_image_url,
                product_url=record.product_url or o.product_url,
            ))
        else:
            merged.append(record)
    return merged
```

### `_process_job()` updated flow:

```python
async def _process_job(self, job_document, run_document):
    # 1. Import raw items
    imported_items, expected_items = await self._load_or_import_raw_items(...)

    # 2. Convert to standard contracts via adapter
    adapter = get_adapter(self._get_adapter_name(job_document.pool_code, 0))
    contracts = [
        c for item in imported_items
        if (c := adapter.to_standard_contract(item.payload, marketplace)) is not None
    ]

    # 3. Null-field pool fallback
    if any(c.has_null_critical_fields() for c in contracts):
        contracts = await self._try_pool_fallback(
            job_document, contracts, run_document,
        )

    # 4. Convert contracts → NormalizedProductRecord (existing normalization)
    normalized = self._contracts_to_normalized(contracts, ...)

    # 5. Snapshot + events (existing)
    ...
```

---

## Deals Flow (No Pool Fallback)

Deals use a single actor. No null-field fallback needed.

```python
async def _dispatch_deals_run(job_document, gateway, config):
    binding_code = "deals:0"
    launch = await gateway.start_run(binding_code, run_input)
    # ... create ApifyRunDocument with pool fields ...
```

---

## Monitoring

New metrics:

```python
# Pool fallback tracking
"apify_pool_fallback_triggered_total"     # pool_code, tracker_type
"apify_pool_fallback_completed_total"     # pool_code, resolved (nulls filled)
"apify_pool_fallback_exhausted_total"     # pool_code, nulls remain
"apify_pool_actor_dispatch_total"         # pool_code, actor_id, pool_index, result
"apify_pool_actor_dispatch_failed_total"  # pool_code, actor_id, error_type

# Adapter tracking
"adapter_conversion_total"               # adapter_name, result (valid/invalid)
```

---

## Migration Plan

### Phase 1: Config + Gateway (backward compatible)

- Add `actor_pools` to config alongside existing `bindings`
- Add `resolve_pool()` to gateway
- `resolve_binding()` still works, reads from old `bindings` config
- New `start_run()` parses `"pool:index"` format, falls back to old format

### Phase 2: Contracts + Adapters

- Add `app/models/contracts.py` with standard contract models
- Add `app/integrations/adapters.py` with adapter implementations
- Add `app/integrations/adapter_registry.py`
- Unit tests for each adapter

### Phase 3: Documents + Orchestrator

- Add `pool_code`, `current_pool_index` to `JobDocument`
- Add `pool_actor_id`, `pool_actor_name`, `pool_index` to `ApifyRunDocument`
- Add `pool_code` to `JobRunStrategy`
- Update `RunOrchestrator.dispatch_job()` to use pool
- Update `job_service.py` to assign `pool_code`
- Backward compat: `binding_code` still populated during migration

### Phase 4: Import Service

- Add `_try_pool_fallback()` and `_merge_contracts()`
- Replace enrichment block in `_process_job()`
- Remove `_enrich_with_junglee()`
- Remove `normalize_junglee_item()`
- Update `_redispatch_category_run()` to use pool

### Phase 5: Cleanup

- Remove old `bindings` config section
- Remove flat `ApifyConfig` binding fields (`category_actor_id`, etc.)
- Remove `resolve_binding()` (or keep as deprecated)
- Remove old enrichment-related code
- Update tests

---

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| Actor schema changes break adapter | Standard contract validates at adapter level; adapter tests catch regressions |
| Pool exhausted with nulls still present | Job marked `PARTIAL_SUCCESS` with error code `POOL_EXHAUSTED_NULL_FIELDS` |
| Adapter not found for pool entry | `get_adapter()` raises at config validation time, fail fast |
| Performance: multiple dispatches per job | Pool fallback only triggers when nulls exist; most jobs use first actor only |
| Backward compat during migration | `binding_code` field coexists with `pool_code`; old dispatch path still works |
