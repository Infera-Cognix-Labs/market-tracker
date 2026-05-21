
# 1. Scope
## 1.1 Category Tracking (broad view)
- Track **Top 50** products for a **specific subcategory** (input = **browse node URL / node ID**, not a broad category)
- Primary signal: **who enters / exits Top 50** 
- Alert logic distinguishes:  
	- **New Entrant** (first time seen since tracking started)
	- **Returning Product** (re-enters after dropping out)  
- Extra layer: **Top 10 enter/exit** alerts (more meaningful sales zone)
  
## 1.2 Competitor Tracking (deep dive)
- Manual selection of **1–50+ ASINs** (typically 10–20) for detailed daily tracking  
- Daily signals for these ASINs: 
	- **BSR position**
	- **Price** 
	- **Buy Box / availability status** (in stock / out of stock / inactive)  
	- **Promotions** (coupon/discount flags when detectable)
	- **Listing change tracking**:  
		- Title change
		- Main image change 
		- Variations added (e.g., new color/size)
		- Enhanced Brand Content / A+ section changes 

## 1.3 Dashboard & reporting
- Dashboard with **switchable timeframes** (daily/weekly/monthly) 
- Visuals: BSR movement over time + event markers (price/listing changes)
- Weekly digest recap (top changes + biggest threats)

  
**_What is feasible (and how we’ll implement it)_**  
- **Top 50 tracking + Top 10 layer:** Yes (daily snapshots + entrant/exit detection)
- **Detailed tracking for selected ASINs (BSR/price/rating):** Yes (daily)
- **Title & main image change alerts:** Yes (hash/URL comparison)
- **Variations added:** Yes (best-effort; depends on listing structure)
- **Buy Box / stock status:** Yes (best-effort; we can reliably detect “unavailable/out of stock” states, Buy Box owner details may vary)
- **Promotions (coupon/discount):** Best-effort (detect when clearly surfaced on page/data feed)
- **content change:** Best-effort (we can flag content/structure changes, but we should expect occasional false positives due to page rendering differences)

Reference Tool:
- Seller Sonar: https://app.sellersonar.com/dashboard
- Helium 10: https://members.helium10.com/dashboard?accountId=1547618947
- Apify: https://apify.com/sovereigntaylor/amazon-bsr-tracker
- AMZ best seller ranking: https://www.amazon.de/-/en/gp/bestsellers/?ref_=nav_em_cs_bestsellers_0_1_1_2
- searched product file: [E:\1_CHI-NOT-CHESE\1_PARA\1. PROJECTS\VISERVE\File Chi.xlsx]

