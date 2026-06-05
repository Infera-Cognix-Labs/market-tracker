# Category Actor
## saswave/amazon-product-scraper
### Input Schema
```json
{
  "search_term": "headphones",
  "marketplace": "amazon.de",
  "maxPages": 5,
  "countryCode": "DE",
  "proxy": {
    "useApifyProxy": true,
    "apifyProxyGroups": ["RESIDENTIAL"]
  }
}
```
### Output Fields
| Field | Type | Description |
|-------|------|-------------|
| asin / ASIN / productAsin | string | Amazon Standard Identification Number |
| title / name | string | Product title |
| brand / manufacturer | string | Product brand |
| url / product_url / productUrl | string | Product page URL |
| image / main_image_url / image_url | string | Main product image |
| price / price_current / deal_price | number | Current price |
| price_original / originalPrice / list_price | number | Original price |
| currency / currencyCode | string | Currency code |
| coupon_text / coupon / promotion_text | string | Coupon/promotion info |
| rating / stars / rating_value | number | Customer rating (0-5) |
| reviewCount / reviewsCount / review_count | number | Total reviews |
| rank_position / rank / position | number | Search result position |
| best_seller_rank / bsr_position | number | BSR rank |
| variation_count / variationCount | number | Number of variations |
| availability_status / availability | string | Stock status |
| buy_box_status / buyBoxStatus | string | Buy box status |
| buy_box_seller_name / buyBoxSellerName / seller_name | string | Buy box seller |

## junglee/amazon-bestsellers
### Input Schema
{
  "categoryUrls": [
    "https://www.amazon.com/Best-Sellers-Electronics/zgbs/electronics/"
  ],
  "maxItemsPerStartUrl": 100,
  "depthOfCrawl": 1,
  "language": "en",
  "detailedInformation": false,
  "useCaptchaSolver": false
}
### Output Definition
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "Product name",
      "nullable": true,
      "example": "Example Wireless Headphones"
    },
    "url": {
      "type": "string",
      "description": "URL of the product page",
      "nullable": true,
      "example": "https://www.amazon.com/dp/B08EXAMPLE01"
    },
    "asin": {
      "type": "string",
      "description": "Amazon Standard Identification Number",
      "nullable": true,
      "example": "B08EXAMPLE01"
    },
    "position": {
      "type": "number",
      "description": "Bestseller rank position within the category",
      "nullable": true,
      "example": 3
    },
    "price": {
      "type": "object",
      "description": "Product price",
      "nullable": true,
      "properties": {
        "value": {
          "type": "number",
          "nullable": true
        },
        "currency": {
          "type": "string",
          "nullable": true
        }
      },
      "required": [],
      "additionalProperties": true,
      "example": {
        "value": 29.99,
        "currency": "USD"
      }
    },
    "currency": {
      "type": "string",
      "description": "Currency code of the product price",
      "nullable": true,
      "example": "USD"
    },
    "numberOfOffers": {
      "type": "number",
      "description": "Number of available purchase offers",
      "nullable": true,
      "example": 5
    },
    "stars": {
      "type": "number",
      "description": "Average customer rating out of 5",
      "nullable": true,
      "example": 4.5
    },
    "reviewsCount": {
      "type": "number",
      "description": "Total number of customer reviews",
      "nullable": true,
      "example": 1250
    },
    "thumbnailUrl": {
      "type": "string",
      "description": "URL of the product thumbnail image",
      "nullable": true,
      "example": "https://m.media-amazon.com/images/I/exampleimage.jpg"
    },
    "categoryUrl": {
      "type": "string",
      "description": "URL of the bestseller category page",
      "nullable": true,
      "example": "https://www.amazon.com/Best-Sellers-Electronics/zgbs/electronics"
    },
    "categoryName": {
      "type": "string",
      "description": "Short category name",
      "nullable": true,
      "example": "Electronics"
    },
    "categoryFullName": {
      "type": "string",
      "description": "Full category name as shown on the bestsellers page",
      "nullable": true,
      "example": "Best Sellers in Electronics"
    },
    "subcategories": {
      "type": "array",
      "description": "Subcategories listed under the bestseller category",
      "nullable": true,
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": []
      },
      "example": [
        {
          "categoryName": "Headphones",
          "categoryUrl": "https://www.amazon.com/Best-Sellers-Electronics-Headphones/zgbs/electronics/13"
        }
      ]
    },
    "input": {
      "type": "string",
      "description": "Input URL that was used to scrape this bestseller",
      "nullable": true,
      "example": "https://www.amazon.com/Best-Sellers-Electronics/zgbs/electronics"
    }
  },
  "required": [],
  "additionalProperties": true
}
## crawlerbros/amazon-bestseller-scraper
### Input Schema
{
  "categoryUrls": [
    "https://www.amazon.com/Best-Sellers-Electronics/zgbs/electronics/",
    "https://www.amazon.de/-/en/gp/movers-and-shakers/garden/",
    "https://www.amazon.co.uk/gp/new-releases/",
    "https://www.amazon.es/gp/most-wished-for/",
    "https://www.amazon.fr/gp/most-gifted/books/"
  ],
  "maxItems": 100,
  "scrapeSubcategories": false,
  "maxSubcategoryDepth": 1,
  "proxyCountry": "AUTO",
  "rateLimitDelay": 2
}
### Output Definition
[
  {
    "position": 1,
    "category": "Amazon Best Sellers: Best Electronics",
    "categoryUrl": "https://www.amazon.com/Best-Sellers-Electronics/zgbs/electronics/",
    "name": "Amazon Fire TV Stick 4K, brilliant 4K streaming quality, TV and smart home controls, free and live TV",
    "asin": "B08XVYZ1Y5",
    "price": 22.99,
    "currency": "$",
    "numberOfOffers": 1,
    "url": "https://www.amazon.com/dp/B08XVYZ1Y5",
    "thumbnail": "https://images-na.ssl-images-amazon.com/images/I/41GYmjbeVSL._AC_UL600_SR600,400_.jpg",
    "rating": 4.5,
    "reviewsCount": 125432,
    "scrapedAt": "2026-01-26T12:00:00.000Z"
  },
  {
    "position": 2,
    "category": "Amazon Best Sellers: Best Electronics",
    "categoryUrl": "https://www.amazon.com/Best-Sellers-Electronics/zgbs/electronics/",
    "name": "Apple AirTag",
    "asin": "B0933BVK6T",
    "price": 28.99,
    "currency": "$",
    "numberOfOffers": 1,
    "url": "https://www.amazon.com/dp/B0933BVK6T",
    "thumbnail": "https://images-na.ssl-images-amazon.com/images/I/713xuNx00oS._AC_UL600_SR600,400_.jpg",
    "rating": 4.7,
    "reviewsCount": 98234,
    "scrapedAt": "2026-01-26T12:00:00.000Z"
  }
]

# Product Actor
## junglee/amazon-crawler
### Input Schema
{
  "categoryOrProductUrls": [
    {
      "url": "https://www.amazon.com/s?k=keyboard"
    }
  ],
  "maxItemsPerStartUrl": 100,
  "language": "en",
  "proxyCountry": "AUTO_SELECT_PROXY_COUNTRY",
  "maxSearchPagesPerStartUrl": 9999,
  "maxOffers": 0,
  "scrapeSellers": false,
  "useCaptchaSolver": false,
  "scrapeProductVariantPrices": false,
  "scrapeProductDetails": true,
  "countryCode": "US",
  "zipCode": "10001",
  "locationDeliverableRoutes": [
    "PRODUCT",
    "SEARCH",
    "OFFERS"
  ]
}
### Output Definition
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "title": {
      "type": "string",
      "description": "Product title",
      "nullable": true,
      "example": "Example Wireless Headphones with Noise Cancelling"
    },
    "url": {
      "type": "string",
      "description": "URL of the product page",
      "nullable": true,
      "example": "https://www.amazon.com/dp/B08EXAMPLE01"
    },
    "asin": {
      "type": "string",
      "description": "Amazon Standard Identification Number",
      "nullable": true,
      "example": "B08EXAMPLE01"
    },
    "originalAsin": {
      "type": "string",
      "description": "Original ASIN before any redirects",
      "nullable": true,
      "example": "B08EXAMPLE01"
    },
    "brand": {
      "type": "string",
      "description": "Product brand name",
      "nullable": true,
      "example": "Example Brand"
    },
    "author": {
      "type": "string",
      "description": "Author name (for books)",
      "nullable": true,
      "example": "Example Author"
    },
    "price": {
      "type": "object",
      "description": "Current product price",
      "nullable": true,
      "properties": {
        "value": {
          "type": "number",
          "nullable": true
        },
        "currency": {
          "type": "string",
          "nullable": true
        }
      },
      "required": [],
      "additionalProperties": true,
      "example": {
        "value": 29.99,
        "currency": "USD"
      }
    },
    "listPrice": {
      "type": "object",
      "description": "Original list price before discounts",
      "nullable": true,
      "properties": {
        "value": {
          "type": "number",
          "nullable": true
        },
        "currency": {
          "type": "string",
          "nullable": true
        }
      },
      "required": [],
      "additionalProperties": true,
      "example": {
        "value": 49.99,
        "currency": "USD"
      }
    },
    "shippingPrice": {
      "type": "object",
      "description": "Shipping cost",
      "nullable": true,
      "properties": {
        "value": {
          "type": "number",
          "nullable": true
        },
        "currency": {
          "type": "string",
          "nullable": true
        }
      },
      "required": [],
      "additionalProperties": true,
      "example": {
        "value": 0,
        "currency": "USD"
      }
    },
    "inStock": {
      "type": "boolean",
      "description": "Whether the product is currently in stock",
      "nullable": true,
      "example": true
    },
    "inStockText": {
      "type": "string",
      "description": "Stock availability text as shown on the page",
      "nullable": true,
      "example": "In Stock"
    },
    "delivery": {
      "type": "string",
      "description": "Delivery information",
      "nullable": true,
      "example": "FREE delivery Monday, April 7"
    },
    "fastestDelivery": {
      "type": "string",
      "description": "Fastest available delivery option",
      "nullable": true,
      "example": "Get it today"
    },
    "condition": {
      "type": "string",
      "description": "Product condition",
      "nullable": true,
      "example": "New"
    },
    "stars": {
      "type": "number",
      "description": "Average customer rating out of 5",
      "nullable": true,
      "example": 4.5
    },
    "starsBreakdown": {
      "type": "object",
      "description": "Percentage breakdown of ratings by star level",
      "nullable": true,
      "additionalProperties": true,
      "required": [],
      "example": {
        "5 star": 72,
        "4 star": 15,
        "3 star": 7,
        "2 star": 3,
        "1 star": 3
      }
    },
    "reviewsCount": {
      "type": "number",
      "description": "Total number of customer reviews",
      "nullable": true,
      "example": 1250
    },
    "answeredQuestions": {
      "type": "number",
      "description": "Number of answered customer questions",
      "nullable": true,
      "example": 45
    },
    "breadCrumbs": {
      "type": "string",
      "description": "Category breadcrumb path",
      "nullable": true,
      "example": "Electronics > Headphones > Over-Ear Headphones"
    },
    "sustainabilityFeatures": {
      "type": "array",
      "description": "Sustainability certifications and features",
      "nullable": true,
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": []
      },
      "example": [
        {
          "title": "Carbon Neutral",
          "description": "This product is carbon neutral certified.",
          "certifiedBy": []
        }
      ]
    },
    "description": {
      "type": "string",
      "description": "Product description",
      "nullable": true,
      "example": "This is an example product description with key features and benefits."
    },
    "features": {
      "type": "array",
      "description": "List of product feature bullet points",
      "nullable": true,
      "items": {
        "type": "string"
      },
      "example": [
        "Noise cancelling technology",
        "30-hour battery life",
        "Foldable design"
      ]
    },
    "videosCount": {
      "type": "number",
      "description": "Number of product videos",
      "nullable": true,
      "example": 2
    },
    "visitStoreLink": {
      "type": "object",
      "description": "Link to visit the brand store page",
      "nullable": true,
      "properties": {
        "text": {
          "type": "string",
          "nullable": true
        },
        "url": {
          "type": "string",
          "nullable": true
        }
      },
      "required": [],
      "additionalProperties": true,
      "example": {
        "text": "Visit the Example Brand Store",
        "url": "https://www.amazon.com/stores/ExampleBrand/page/EXAMPLEID"
      }
    },
    "thumbnailImage": {
      "type": "string",
      "description": "URL of the product thumbnail image",
      "nullable": true,
      "example": "https://m.media-amazon.com/images/I/exampleimage.jpg"
    },
    "galleryThumbnails": {
      "type": "array",
      "description": "URLs of gallery thumbnail images",
      "nullable": true,
      "items": {
        "type": "string"
      },
      "example": [
        "https://m.media-amazon.com/images/I/example1.jpg",
        "https://m.media-amazon.com/images/I/example2.jpg"
      ]
    },
    "highResolutionImages": {
      "type": "array",
      "description": "URLs of high-resolution product images",
      "nullable": true,
      "items": {
        "type": "string"
      },
      "example": [
        "https://m.media-amazon.com/images/I/examplehires.jpg"
      ]
    },
    "importantInformation": {
      "type": "object",
      "description": "Important product information section",
      "nullable": true,
      "properties": {
        "title": {
          "type": "string",
          "nullable": true
        },
        "items": {
          "type": "array",
          "nullable": true,
          "items": {
            "type": "object",
            "additionalProperties": true,
            "required": []
          }
        }
      },
      "required": [],
      "additionalProperties": true,
      "example": {
        "title": "Safety Information",
        "items": [
          {
            "title": "Warning",
            "text": "Keep out of reach of children.",
            "url": null
          }
        ]
      }
    },
    "returnPolicy": {
      "type": "string",
      "description": "Return policy information",
      "nullable": true,
      "example": "30-day return period"
    },
    "support": {
      "type": "string",
      "description": "Product support information",
      "nullable": true,
      "example": "1-year manufacturer warranty"
    },
    "variantAsins": {
      "type": "array",
      "description": "ASINs of all product variants",
      "nullable": true,
      "items": {
        "type": "string"
      },
      "example": [
        "B08EXAMPLE02",
        "B08EXAMPLE03"
      ]
    },
    "variantDetails": {
      "type": "array",
      "description": "Detailed information about each product variant",
      "nullable": true,
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": []
      },
      "example": [
        {
          "asin": "B08EXAMPLE02",
          "price": {
            "value": 34.99,
            "currency": "USD"
          },
          "name": "Black",
          "images": [],
          "thumbnail": null
        }
      ]
    },
    "reviewsLink": {
      "type": "string",
      "description": "URL to the product reviews page",
      "nullable": true,
      "example": "https://www.amazon.com/product-reviews/B08EXAMPLE01"
    },
    "hasReviews": {
      "type": "boolean",
      "description": "Whether the product has customer reviews",
      "nullable": true,
      "example": true
    },
    "variantAttributes": {
      "type": "array",
      "description": "Attributes that differentiate product variants (e.g., color, size)",
      "nullable": true,
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": []
      },
      "example": [
        {
          "key": "Color",
          "value": "Black"
        },
        {
          "key": "Size",
          "value": "Standard"
        }
      ]
    },
    "attributes": {
      "type": "array",
      "description": "Product technical specifications and attributes",
      "nullable": true,
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": []
      },
      "example": [
        {
          "key": "Manufacturer",
          "value": "Example Brand"
        },
        {
          "key": "Item Weight",
          "value": "0.55 pounds"
        }
      ]
    },
    "attributesMapped": {
      "type": "object",
      "description": "Product attributes as a flat key-value map (alternative representation of attributes)",
      "nullable": true,
      "additionalProperties": true,
      "required": [],
      "example": {
        "Manufacturer": "Example Brand",
        "Item Weight": "0.55 pounds"
      }
    },
    "productOverview": {
      "type": "array",
      "description": "Product overview specifications displayed prominently on the page",
      "nullable": true,
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": []
      },
      "example": [
        {
          "key": "Brand",
          "value": "Example Brand"
        },
        {
          "key": "Model Number",
          "value": "EX-100"
        }
      ]
    },
    "manufacturerAttributes": {
      "type": "array",
      "description": "Manufacturer-provided product attributes",
      "nullable": true,
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": []
      },
      "example": [
        {
          "key": "Battery Life",
          "value": "30 hours"
        }
      ]
    },
    "seller": {
      "type": "object",
      "description": "Seller information for the product listing",
      "nullable": true,
      "additionalProperties": true,
      "required": [],
      "example": {
        "id": "EXAMPLESELLERID",
        "name": "Example Seller",
        "url": "https://www.amazon.com/sp?seller=EXAMPLESELLERID"
      }
    },
    "bestsellerRanks": {
      "type": "array",
      "description": "Bestseller rankings across Amazon categories",
      "nullable": true,
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": []
      },
      "example": [
        {
          "rank": 42,
          "category": "Electronics",
          "url": "https://www.amazon.com/Best-Sellers-Electronics/zgbs/electronics"
        }
      ]
    },
    "isAmazonChoice": {
      "type": "boolean",
      "description": "Whether the product has the Amazon's Choice badge",
      "nullable": true,
      "example": false
    },
    "amazonChoiceText": {
      "type": "string",
      "description": "Amazon's Choice label text",
      "nullable": true,
      "example": "Amazon's Choice in Wireless Headphones"
    },
    "bookDescription": {
      "type": "string",
      "description": "Extended description for books",
      "nullable": true,
      "example": "This is an example book description."
    },
    "priceRange": {
      "type": "object",
      "description": "Price range for products with multiple price variants",
      "nullable": true,
      "properties": {
        "min": {
          "type": "object",
          "nullable": true,
          "additionalProperties": true,
          "required": []
        },
        "max": {
          "type": "object",
          "nullable": true,
          "additionalProperties": true,
          "required": []
        }
      },
      "required": [],
      "additionalProperties": true,
      "example": {
        "min": {
          "value": 19.99,
          "currency": "USD"
        },
        "max": {
          "value": 49.99,
          "currency": "USD"
        }
      }
    },
    "aPlusContent": {
      "type": "object",
      "description": "Amazon A+ enhanced brand content",
      "nullable": true,
      "additionalProperties": true,
      "required": [],
      "example": {
        "title": "About Example Brand",
        "rawText": "Example brand story text.",
        "rawImages": [],
        "rawVideos": [],
        "modules": []
      }
    },
    "brandStory": {
      "type": "object",
      "description": "Brand story section content",
      "nullable": true,
      "additionalProperties": true,
      "required": [],
      "example": {
        "title": "Our Story",
        "image": null,
        "items": []
      }
    },
    "productComparison": {
      "type": "object",
      "description": "Product comparison table with competing products",
      "nullable": true,
      "additionalProperties": true,
      "required": [],
      "example": {
        "title": "Compare with similar items",
        "items": []
      }
    },
    "aiReviewsSummary": {
      "type": "object",
      "description": "AI-generated summary of customer reviews",
      "nullable": true,
      "additionalProperties": true,
      "required": [],
      "example": {
        "text": "Customers appreciate the sound quality and comfortable fit.",
        "keywords": []
      }
    },
    "monthlyPurchaseVolume": {
      "type": "string",
      "description": "Estimated monthly purchase volume shown on the product page",
      "nullable": true,
      "example": "1K+ bought in past month"
    },
    "productPageReviews": {
      "type": "array",
      "description": "Sample reviews shown on the product detail page",
      "nullable": true,
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": []
      },
      "example": [
        {
          "username": "ExampleUser",
          "ratingScore": 5,
          "reviewTitle": "Great product!",
          "reviewDescription": "Really happy with this purchase.",
          "date": "2025-01-15T12:00:00.000Z"
        }
      ]
    },
    "productPageReviewsFromOtherCountries": {
      "type": "array",
      "description": "Sample reviews from other countries shown on the product page",
      "nullable": true,
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": []
      },
      "example": []
    },
    "offers": {
      "type": "array",
      "description": "Available purchase offers from different sellers",
      "nullable": true,
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": []
      },
      "example": [
        {
          "url": "https://www.amazon.com/gp/offer-listing/B08EXAMPLE01",
          "condition": "New",
          "price": {
            "value": 29.99,
            "currency": "USD"
          },
          "seller": {
            "name": "Example Seller"
          },
          "position": 1,
          "isPinnedOffer": true
        }
      ]
    },
    "locationText": {
      "type": "string",
      "description": "Delivery location text shown on the product page",
      "nullable": true,
      "example": "Delivering to New York 10001"
    },
    "unNormalizedProductUrl": {
      "type": "string",
      "description": "Original product URL before normalization",
      "nullable": true,
      "example": "https://www.amazon.com/Example-Product-Title/dp/B08EXAMPLE01/ref=sr_1_1"
    },
    "loadedCountryCode": {
      "type": "string",
      "description": "Country code of the Amazon domain that was scraped",
      "nullable": true,
      "example": "US"
    },
    "categoryPageData": {
      "type": "object",
      "description": "Additional data from the category listing page where the product was found",
      "nullable": true,
      "properties": {
        "categoryUrl": {
          "type": "string",
          "nullable": true
        },
        "saleSummary": {
          "type": "string",
          "nullable": true
        },
        "isSponsored": {
          "type": "boolean",
          "nullable": true
        },
        "bestsellerBadge": {
          "type": "string",
          "nullable": true
        },
        "productPosition": {
          "type": "number",
          "nullable": true
        },
        "pageNumber": {
          "type": "number",
          "nullable": true
        }
      },
      "required": [],
      "additionalProperties": true,
      "example": {
        "categoryUrl": "https://www.amazon.com/s?k=headphones",
        "saleSummary": null,
        "isSponsored": false,
        "bestsellerBadge": null,
        "productPosition": 3,
        "pageNumber": 1
      }
    },
    "bestsellerPageData": {
      "type": "object",
      "description": "Additional data from the bestsellers page where the product was found",
      "nullable": true,
      "properties": {
        "position": {
          "type": "number",
          "nullable": true
        },
        "categoryUrl": {
          "type": "string",
          "nullable": true
        },
        "categoryName": {
          "type": "string",
          "nullable": true
        },
        "categoryFullName": {
          "type": "string",
          "nullable": true
        }
      },
      "required": [],
      "additionalProperties": true,
      "example": {
        "position": 5,
        "categoryUrl": "https://www.amazon.com/Best-Sellers-Electronics/zgbs/electronics",
        "categoryName": "Electronics",
        "categoryFullName": "Best Sellers in Electronics"
      }
    },
    "input": {
      "type": "string",
      "description": "Input URL that was used to scrape this product",
      "nullable": true,
      "example": "https://www.amazon.com/dp/B08EXAMPLE01"
    }
  },
  "required": [],
  "additionalProperties": true
}
## junglee/amazon-asins-scraper
### Input Schema
{
  "asins": [
    "B07GBZ4Q68"
  ],
  "amazonDomain": "amazon.com",
  "language": "en",
  "proxyCountry": "AUTO_SELECT_PROXY_COUNTRY",
  "useCaptchaSolver": false
}
### Output Definition
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "title": {
      "type": "string",
      "description": "Product title",
      "nullable": true,
      "example": "Example Wireless Headphones with Noise Cancelling"
    },
    "url": {
      "type": "string",
      "description": "URL of the product page",
      "nullable": true,
      "example": "https://www.amazon.com/dp/B08EXAMPLE01"
    },
    "asin": {
      "type": "string",
      "description": "Amazon Standard Identification Number",
      "nullable": true,
      "example": "B08EXAMPLE01"
    },
    "originalAsin": {
      "type": "string",
      "description": "Original ASIN before any redirects",
      "nullable": true,
      "example": "B08EXAMPLE01"
    },
    "brand": {
      "type": "string",
      "description": "Product brand name",
      "nullable": true,
      "example": "Example Brand"
    },
    "author": {
      "type": "string",
      "description": "Author name (for books)",
      "nullable": true,
      "example": "Example Author"
    },
    "price": {
      "type": "object",
      "description": "Current product price",
      "nullable": true,
      "properties": {
        "value": {
          "type": "number",
          "nullable": true
        },
        "currency": {
          "type": "string",
          "nullable": true
        }
      },
      "required": [],
      "additionalProperties": true,
      "example": {
        "value": 29.99,
        "currency": "USD"
      }
    },
    "listPrice": {
      "type": "object",
      "description": "Original list price before discounts",
      "nullable": true,
      "properties": {
        "value": {
          "type": "number",
          "nullable": true
        },
        "currency": {
          "type": "string",
          "nullable": true
        }
      },
      "required": [],
      "additionalProperties": true,
      "example": {
        "value": 49.99,
        "currency": "USD"
      }
    },
    "shippingPrice": {
      "type": "object",
      "description": "Shipping cost",
      "nullable": true,
      "properties": {
        "value": {
          "type": "number",
          "nullable": true
        },
        "currency": {
          "type": "string",
          "nullable": true
        }
      },
      "required": [],
      "additionalProperties": true,
      "example": {
        "value": 0,
        "currency": "USD"
      }
    },
    "inStock": {
      "type": "boolean",
      "description": "Whether the product is currently in stock",
      "nullable": true,
      "example": true
    },
    "inStockText": {
      "type": "string",
      "description": "Stock availability text as shown on the page",
      "nullable": true,
      "example": "In Stock"
    },
    "delivery": {
      "type": "string",
      "description": "Delivery information",
      "nullable": true,
      "example": "FREE delivery Monday, April 7"
    },
    "fastestDelivery": {
      "type": "string",
      "description": "Fastest available delivery option",
      "nullable": true,
      "example": "Get it today"
    },
    "condition": {
      "type": "string",
      "description": "Product condition",
      "nullable": true,
      "example": "New"
    },
    "stars": {
      "type": "number",
      "description": "Average customer rating out of 5",
      "nullable": true,
      "example": 4.5
    },
    "starsBreakdown": {
      "type": "object",
      "description": "Percentage breakdown of ratings by star level",
      "nullable": true,
      "additionalProperties": true,
      "required": [],
      "example": {
        "5 star": 72,
        "4 star": 15,
        "3 star": 7,
        "2 star": 3,
        "1 star": 3
      }
    },
    "reviewsCount": {
      "type": "number",
      "description": "Total number of customer reviews",
      "nullable": true,
      "example": 1250
    },
    "answeredQuestions": {
      "type": "number",
      "description": "Number of answered customer questions",
      "nullable": true,
      "example": 45
    },
    "breadCrumbs": {
      "type": "string",
      "description": "Category breadcrumb path",
      "nullable": true,
      "example": "Electronics > Headphones > Over-Ear Headphones"
    },
    "sustainabilityFeatures": {
      "type": "array",
      "description": "Sustainability certifications and features",
      "nullable": true,
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": []
      },
      "example": [
        {
          "title": "Carbon Neutral",
          "description": "This product is carbon neutral certified.",
          "certifiedBy": []
        }
      ]
    },
    "description": {
      "type": "string",
      "description": "Product description",
      "nullable": true,
      "example": "This is an example product description with key features and benefits."
    },
    "features": {
      "type": "array",
      "description": "List of product feature bullet points",
      "nullable": true,
      "items": {
        "type": "string"
      },
      "example": [
        "Noise cancelling technology",
        "30-hour battery life",
        "Foldable design"
      ]
    },
    "videosCount": {
      "type": "number",
      "description": "Number of product videos",
      "nullable": true,
      "example": 2
    },
    "visitStoreLink": {
      "type": "object",
      "description": "Link to visit the brand store page",
      "nullable": true,
      "properties": {
        "text": {
          "type": "string",
          "nullable": true
        },
        "url": {
          "type": "string",
          "nullable": true
        }
      },
      "required": [],
      "additionalProperties": true,
      "example": {
        "text": "Visit the Example Brand Store",
        "url": "https://www.amazon.com/stores/ExampleBrand/page/EXAMPLEID"
      }
    },
    "thumbnailImage": {
      "type": "string",
      "description": "URL of the product thumbnail image",
      "nullable": true,
      "example": "https://m.media-amazon.com/images/I/exampleimage.jpg"
    },
    "galleryThumbnails": {
      "type": "array",
      "description": "URLs of gallery thumbnail images",
      "nullable": true,
      "items": {
        "type": "string"
      },
      "example": [
        "https://m.media-amazon.com/images/I/example1.jpg",
        "https://m.media-amazon.com/images/I/example2.jpg"
      ]
    },
    "highResolutionImages": {
      "type": "array",
      "description": "URLs of high-resolution product images",
      "nullable": true,
      "items": {
        "type": "string"
      },
      "example": [
        "https://m.media-amazon.com/images/I/examplehires.jpg"
      ]
    },
    "importantInformation": {
      "type": "object",
      "description": "Important product information section",
      "nullable": true,
      "properties": {
        "title": {
          "type": "string",
          "nullable": true
        },
        "items": {
          "type": "array",
          "nullable": true,
          "items": {
            "type": "object",
            "additionalProperties": true,
            "required": []
          }
        }
      },
      "required": [],
      "additionalProperties": true,
      "example": {
        "title": "Safety Information",
        "items": [
          {
            "title": "Warning",
            "text": "Keep out of reach of children.",
            "url": null
          }
        ]
      }
    },
    "returnPolicy": {
      "type": "string",
      "description": "Return policy information",
      "nullable": true,
      "example": "30-day return period"
    },
    "support": {
      "type": "string",
      "description": "Product support information",
      "nullable": true,
      "example": "1-year manufacturer warranty"
    },
    "variantAsins": {
      "type": "array",
      "description": "ASINs of all product variants",
      "nullable": true,
      "items": {
        "type": "string"
      },
      "example": [
        "B08EXAMPLE02",
        "B08EXAMPLE03"
      ]
    },
    "variantDetails": {
      "type": "array",
      "description": "Detailed information about each product variant",
      "nullable": true,
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": []
      },
      "example": [
        {
          "asin": "B08EXAMPLE02",
          "price": {
            "value": 34.99,
            "currency": "USD"
          },
          "name": "Black",
          "images": [],
          "thumbnail": null
        }
      ]
    },
    "reviewsLink": {
      "type": "string",
      "description": "URL to the product reviews page",
      "nullable": true,
      "example": "https://www.amazon.com/product-reviews/B08EXAMPLE01"
    },
    "hasReviews": {
      "type": "boolean",
      "description": "Whether the product has customer reviews",
      "nullable": true,
      "example": true
    },
    "variantAttributes": {
      "type": "array",
      "description": "Attributes that differentiate product variants (e.g., color, size)",
      "nullable": true,
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": []
      },
      "example": [
        {
          "key": "Color",
          "value": "Black"
        },
        {
          "key": "Size",
          "value": "Standard"
        }
      ]
    },
    "attributes": {
      "type": "array",
      "description": "Product technical specifications and attributes",
      "nullable": true,
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": []
      },
      "example": [
        {
          "key": "Manufacturer",
          "value": "Example Brand"
        },
        {
          "key": "Item Weight",
          "value": "0.55 pounds"
        }
      ]
    },
    "attributesMapped": {
      "type": "object",
      "description": "Product attributes as a flat key-value map (alternative representation of attributes)",
      "nullable": true,
      "additionalProperties": true,
      "required": [],
      "example": {
        "Manufacturer": "Example Brand",
        "Item Weight": "0.55 pounds"
      }
    },
    "productOverview": {
      "type": "array",
      "description": "Product overview specifications displayed prominently on the page",
      "nullable": true,
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": []
      },
      "example": [
        {
          "key": "Brand",
          "value": "Example Brand"
        },
        {
          "key": "Model Number",
          "value": "EX-100"
        }
      ]
    },
    "manufacturerAttributes": {
      "type": "array",
      "description": "Manufacturer-provided product attributes",
      "nullable": true,
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": []
      },
      "example": [
        {
          "key": "Battery Life",
          "value": "30 hours"
        }
      ]
    },
    "seller": {
      "type": "object",
      "description": "Seller information for the product listing",
      "nullable": true,
      "additionalProperties": true,
      "required": [],
      "example": {
        "id": "EXAMPLESELLERID",
        "name": "Example Seller",
        "url": "https://www.amazon.com/sp?seller=EXAMPLESELLERID"
      }
    },
    "bestsellerRanks": {
      "type": "array",
      "description": "Bestseller rankings across Amazon categories",
      "nullable": true,
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": []
      },
      "example": [
        {
          "rank": 42,
          "category": "Electronics",
          "url": "https://www.amazon.com/Best-Sellers-Electronics/zgbs/electronics"
        }
      ]
    },
    "isAmazonChoice": {
      "type": "boolean",
      "description": "Whether the product has the Amazon's Choice badge",
      "nullable": true,
      "example": false
    },
    "amazonChoiceText": {
      "type": "string",
      "description": "Amazon's Choice label text",
      "nullable": true,
      "example": "Amazon's Choice in Wireless Headphones"
    },
    "bookDescription": {
      "type": "string",
      "description": "Extended description for books",
      "nullable": true,
      "example": "This is an example book description."
    },
    "priceRange": {
      "type": "object",
      "description": "Price range for products with multiple price variants",
      "nullable": true,
      "properties": {
        "min": {
          "type": "object",
          "nullable": true,
          "additionalProperties": true,
          "required": []
        },
        "max": {
          "type": "object",
          "nullable": true,
          "additionalProperties": true,
          "required": []
        }
      },
      "required": [],
      "additionalProperties": true,
      "example": {
        "min": {
          "value": 19.99,
          "currency": "USD"
        },
        "max": {
          "value": 49.99,
          "currency": "USD"
        }
      }
    },
    "aPlusContent": {
      "type": "object",
      "description": "Amazon A+ enhanced brand content",
      "nullable": true,
      "additionalProperties": true,
      "required": [],
      "example": {
        "title": "About Example Brand",
        "rawText": "Example brand story text.",
        "rawImages": [],
        "rawVideos": [],
        "modules": []
      }
    },
    "brandStory": {
      "type": "object",
      "description": "Brand story section content",
      "nullable": true,
      "additionalProperties": true,
      "required": [],
      "example": {
        "title": "Our Story",
        "image": null,
        "items": []
      }
    },
    "productComparison": {
      "type": "object",
      "description": "Product comparison table with competing products",
      "nullable": true,
      "additionalProperties": true,
      "required": [],
      "example": {
        "title": "Compare with similar items",
        "items": []
      }
    },
    "aiReviewsSummary": {
      "type": "object",
      "description": "AI-generated summary of customer reviews",
      "nullable": true,
      "additionalProperties": true,
      "required": [],
      "example": {
        "text": "Customers appreciate the sound quality and comfortable fit.",
        "keywords": []
      }
    },
    "monthlyPurchaseVolume": {
      "type": "string",
      "description": "Estimated monthly purchase volume shown on the product page",
      "nullable": true,
      "example": "1K+ bought in past month"
    },
    "productPageReviews": {
      "type": "array",
      "description": "Sample reviews shown on the product detail page",
      "nullable": true,
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": []
      },
      "example": [
        {
          "username": "ExampleUser",
          "ratingScore": 5,
          "reviewTitle": "Great product!",
          "reviewDescription": "Really happy with this purchase.",
          "date": "2025-01-15T12:00:00.000Z"
        }
      ]
    },
    "productPageReviewsFromOtherCountries": {
      "type": "array",
      "description": "Sample reviews from other countries shown on the product page",
      "nullable": true,
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": []
      },
      "example": []
    },
    "offers": {
      "type": "array",
      "description": "Available purchase offers from different sellers",
      "nullable": true,
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": []
      },
      "example": [
        {
          "url": "https://www.amazon.com/gp/offer-listing/B08EXAMPLE01",
          "condition": "New",
          "price": {
            "value": 29.99,
            "currency": "USD"
          },
          "seller": {
            "name": "Example Seller"
          },
          "position": 1,
          "isPinnedOffer": true
        }
      ]
    },
    "locationText": {
      "type": "string",
      "description": "Delivery location text shown on the product page",
      "nullable": true,
      "example": "Delivering to New York 10001"
    },
    "unNormalizedProductUrl": {
      "type": "string",
      "description": "Original product URL before normalization",
      "nullable": true,
      "example": "https://www.amazon.com/Example-Product-Title/dp/B08EXAMPLE01/ref=sr_1_1"
    },
    "loadedCountryCode": {
      "type": "string",
      "description": "Country code of the Amazon domain that was scraped",
      "nullable": true,
      "example": "US"
    },
    "categoryPageData": {
      "type": "object",
      "description": "Additional data from the category listing page where the product was found",
      "nullable": true,
      "properties": {
        "categoryUrl": {
          "type": "string",
          "nullable": true
        },
        "saleSummary": {
          "type": "string",
          "nullable": true
        },
        "isSponsored": {
          "type": "boolean",
          "nullable": true
        },
        "bestsellerBadge": {
          "type": "string",
          "nullable": true
        },
        "productPosition": {
          "type": "number",
          "nullable": true
        },
        "pageNumber": {
          "type": "number",
          "nullable": true
        }
      },
      "required": [],
      "additionalProperties": true,
      "example": {
        "categoryUrl": "https://www.amazon.com/s?k=headphones",
        "saleSummary": null,
        "isSponsored": false,
        "bestsellerBadge": null,
        "productPosition": 3,
        "pageNumber": 1
      }
    },
    "bestsellerPageData": {
      "type": "object",
      "description": "Additional data from the bestsellers page where the product was found",
      "nullable": true,
      "properties": {
        "position": {
          "type": "number",
          "nullable": true
        },
        "categoryUrl": {
          "type": "string",
          "nullable": true
        },
        "categoryName": {
          "type": "string",
          "nullable": true
        },
        "categoryFullName": {
          "type": "string",
          "nullable": true
        }
      },
      "required": [],
      "additionalProperties": true,
      "example": {
        "position": 5,
        "categoryUrl": "https://www.amazon.com/Best-Sellers-Electronics/zgbs/electronics",
        "categoryName": "Electronics",
        "categoryFullName": "Best Sellers in Electronics"
      }
    },
    "input": {
      "type": "string",
      "description": "Input URL that was used to scrape this product",
      "nullable": true,
      "example": "https://www.amazon.com/dp/B08EXAMPLE01"
    }
  },
  "required": [],
  "additionalProperties": true
}
# Deals Actor
## hJNp8X1wuz14Wc5wU (Deals Scraper)
### Input Schema
```json
{
  "marketplace": "amazon.de",
  "maxResults": 100,
  "proxy": {
    "useApifyProxy": true,
    "apifyProxyGroups": ["RESIDENTIAL"]
  }
}
```
### Output Fields
| Field | Type | Description |
|-------|------|-------------|
| asin / ASIN | string | Amazon Standard Identification Number |
| deal_state / dealState | string | Current state of the deal |
| deal_type / dealType | string | Type of deal (Lightning, Deal of the Day, etc.) |
| deal_price / dealPrice | number | Deal price |
| list_price / listPrice | number | Original list price |
| savings_percentage / savingsPercentage | number | Percentage savings |
| deal_badge / dealBadge | string | Deal badge text |
| deal_id / dealId | string | Unique deal identifier |
