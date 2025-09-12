# Complete Kibana Dashboard Guide for Real Estate Analytics

## Table of Contents
1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Understanding Your Data](#understanding-your-data)
4. [Setting Up Kibana](#setting-up-kibana)
5. [Creating Data Views](#creating-data-views)
6. [Dashboard 1: Neighborhood Statistics (Demo 4)](#dashboard-1-neighborhood-statistics-demo-4)
7. [Dashboard 2: Price Distribution Analysis (Demo 5)](#dashboard-2-price-distribution-analysis-demo-5)
8. [Advanced Dashboard Techniques](#advanced-dashboard-techniques)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

## Introduction

This guide will teach you how to create stunning, interactive Kibana dashboards for real estate data visualization. We'll build two comprehensive dashboards based on demos 4 and 5 from the es-manager.sh script:

- **Dashboard 1**: Neighborhood Statistics Analysis - Comparing neighborhoods by various metrics
- **Dashboard 2**: Price Distribution Analysis - Understanding market pricing patterns

### What is Kibana?

Kibana is Elasticsearch's data visualization platform. Think of it as Excel's charts on steroids - it allows you to:
- Create interactive visualizations from your data
- Build real-time dashboards
- Explore data through searches and filters
- Share insights with stakeholders

### Why These Dashboards Matter

These dashboards will help you:
- **Identify market opportunities** by comparing neighborhood metrics
- **Understand pricing patterns** to make informed investment decisions
- **Track market trends** over time
- **Present data professionally** to clients or stakeholders

## Prerequisites

### Required Software

1. **Elasticsearch** running on port 9200
2. **Kibana** (we'll install this)
3. **Data loaded** via the pipeline (demos 4 and 5 should work)

### Installing Kibana

```bash
# Using Docker (recommended for beginners)
docker run -d \
  --name kibana \
  --link elasticsearch:elasticsearch \
  -p 5601:5601 \
  -e "ELASTICSEARCH_HOSTS=http://elasticsearch:9200" \
  docker.elastic.co/kibana/kibana:8.11.0

# Wait 2-3 minutes for Kibana to start
# Then open: http://localhost:5601
```

### Verify Your Data

Before starting, ensure your data is loaded:

```bash
# Check if properties index exists
curl -X GET "localhost:9200/properties/_count?pretty"

# Should return something like:
# {
#   "count" : 440,
#   "_shards" : {...}
# }
```

## Understanding Your Data

### Data Structure for Demo 4 (Neighborhood Statistics)

The properties index contains these key fields:
- `neighborhood_id`: Unique identifier for each neighborhood
- `listing_price`: Property price
- `bedrooms`: Number of bedrooms
- `square_feet`: Property size
- `property_type`: Condo, Single-Family, Townhome, etc.
- `location`: Geographic coordinates

### Data Structure for Demo 5 (Price Distribution)

Same index, but we'll focus on:
- `listing_price`: For histogram creation
- `property_type`: For categorical breakdowns
- Statistical aggregations (percentiles, averages)

## Setting Up Kibana

### Step 1: First Login

1. Open http://localhost:5601 in your browser
2. If prompted for authentication:
   - Username: `elastic`
   - Password: Check your `.env` file for `ES_PASSWORD`
3. Skip the welcome tour (we'll guide you better!)

### Step 2: Navigate to Stack Management

1. Click the **hamburger menu** (☰) in the top-left corner
2. Scroll down to **Management** section
3. Click **Stack Management**

### Step 3: Create Your First Data View

Data Views (formerly Index Patterns) tell Kibana which Elasticsearch indices to query.

1. In Stack Management, click **Data Views** under "Kibana" section
2. Click **Create data view**
3. Fill in:
   - **Name**: `Real Estate Properties`
   - **Index pattern**: `properties*` (the asterisk allows future indices)
   - **Timestamp field**: Select `@timestamp` if available, or leave as "No time field"
4. Click **Save data view to Kibana**

### Understanding Data Views

Think of a Data View as a "lens" through which Kibana looks at your data. It defines:
- Which indices to query
- How fields should be formatted
- Which fields are searchable/aggregatable

## Dashboard 1: Neighborhood Statistics (Demo 4)

This dashboard replicates and enhances Demo 4's neighborhood analysis.

### Vision for This Dashboard

We'll create a comprehensive neighborhood comparison dashboard with:
- Choropleth map showing neighborhood metrics
- Bar charts comparing average prices
- Data tables with detailed statistics
- Interactive filters for deep analysis

### Prerequisites: Create Neighborhood Data View

**IMPORTANT**: For neighborhood-level aggregations, you need a dedicated Data View:

1. Go to **Stack Management** → **Data Views**
2. Click **Create data view**
3. Configure:
   - **Name**: `Neighborhoods`
   - **Index pattern**: `properties*`
   - **Time field**: None (unless you have timestamps)
4. After creation, add a **Runtime Field** for price per square foot:
   - Click **Add field**
   - Name: `price_per_sqft`
   - Type: `number`
   - Script:
   ```painless
   if (doc['square_feet'].size() > 0 && doc['square_feet'].value > 0) {
     emit(doc['listing_price'].value / doc['square_feet'].value);
   }
   ```
5. **Save data view**

### Step 1: Create the Dashboard

1. Click the hamburger menu (☰)
2. Navigate to **Analytics** → **Dashboard**
3. Click **Create dashboard**
4. Name it: "Neighborhood Real Estate Analytics"

### Step 2: Visualization 1 - Choropleth Map (Neighborhood Metrics)

**Purpose**: Visual geographic distribution showing aggregated neighborhood metrics

**Option A: Using Maps with Choropleth Layer (Recommended for Custom Boundaries)**

1. Click **Create visualization**
2. Choose **Maps**
3. Click **Add layer** → **Choropleth**
4. Configure the **Boundaries source**:
   - If you have custom neighborhood GeoJSON:
     - Select **Upload GeoJSON**
     - Upload your neighborhood boundaries file
     - Set **Join field**: `neighborhood_id` (or matching property)
   - If using points only:
     - Skip to Option B below
5. Configure the **Statistics source**:
   - **Data view**: `Neighborhoods`
   - **Join field**: `neighborhood_id.keyword`
   - **Metrics**:
     - Metric 1: Count (label: "Properties")
     - Metric 2: Average of `listing_price` (label: "Avg Price")
     - Metric 3: Average of `price_per_sqft` (label: "$/sqft")
6. Style configuration:
   - **Fill color**: By value → Select metric (e.g., Average Price)
   - **Color ramp**: Green to Red
   - **Border color**: Dark grey
   - **Border width**: 1
7. **Tooltip configuration**:
   - Show all metrics
   - Format prices with currency
8. Click **Save and return**

**Option B: Using Documents Layer with Clustering (When No Boundaries Available)**

1. Click **Create visualization**
2. Choose **Maps**
3. Click **Add layer** → **Documents**
4. Configure:
   - **Data view**: `Real Estate Properties`
   - **Geo field**: `location` (or `location.coordinates`)
   - **Scaling**: Clusters
   - **Grid resolution**: Fine
5. Aggregation metrics for clusters:
   - Count of documents
   - Average of `listing_price`
   - Average of `bedrooms`
6. Style configuration:
   - **Fill color**: By value → Average price
   - **Symbol size**: By value → Count
   - **Color palette**: Cool to Warm
7. Click **Save and return**

**Pro Tips**:
- For choropleth maps, neighborhood boundaries (GeoJSON) provide the best visualization
- If you don't have boundaries, use grid aggregation or clustering
- Consider creating custom neighborhood boundaries using tools like geojson.io

### Step 3: Visualization 2 - Average Price by Neighborhood (Bar Chart)

**Data View Required**: `Neighborhoods`

**Purpose**: Compare neighborhoods by average property price

1. Click **Create visualization**
2. Choose **Lens**
3. Drag `neighborhood_id` to the **Horizontal axis**
4. For the Vertical axis:
   - Click the **+** button
   - Choose `listing_price`
   - Change function from "Count" to **Average**
5. Configuration tweaks:
   ```
   Chart Type: Bar vertical stacked
   Value labels: Show
   Legend: Hide (not needed for single metric)
   Missing values: Don't show
   ```
6. Sort configuration:
   - Click the gear icon on horizontal axis
   - **Sort by**: Metric (Average of listing_price)
   - **Direction**: Descending
   - **Number of values**: 20 (top neighborhoods)
7. Name it: "Average Property Price by Neighborhood"
8. **Save and return**

### Step 4: Visualization 3 - Property Count Distribution (Donut Chart)

**Data View Required**: `Neighborhoods`

**Purpose**: Show distribution of properties across neighborhoods

1. **Create visualization** → **Lens**
2. Drag `neighborhood_id` to the **Slice by** field
3. Configuration:
   ```
   Chart Type: Donut
   Value: Count of records
   Number of slices: 15
   Other: Group remaining values
   ```
4. Legend settings:
   - Position: Right
   - Show values in legend: Yes
   - Truncate legend text: 20 characters
5. Name: "Property Distribution by Neighborhood"
6. **Save and return**

### Step 5: Visualization 4 - Detailed Statistics Table

**Data View Required**: `Neighborhoods`

**Purpose**: Comprehensive neighborhood comparison table (like Demo 4's output)

1. **Create visualization** → **Lens**
2. Change to **Table** visualization
3. Build columns:
   
   **Column 1 - Neighborhood**:
   - Drag `neighborhood_id` to Rows
   - Top values: 20
   
   **Column 2 - Property Count**:
   - Add metric: Count of records
   - Name: "Properties"
   
   **Column 3 - Average Price**:
   - Add metric: Average of `listing_price`
   - Format: $0,0
   
   **Column 4 - Price Range**:
   - Add metric: Max of `listing_price`
   - Subtract Min of `listing_price` (use formula if available)
   - Format: $0,0
   
   **Column 5 - Avg Bedrooms**:
   - Add metric: Average of `bedrooms`
   - Format: 0.0
   
   **Column 6 - Avg Sq Ft**:
   - Add metric: Average of `square_feet`
   - Format: 0,0
   
   **Column 7 - Price per Sq Ft**:
   - Create calculated field: `listing_price` / `square_feet`
   - Add as Average
   - Format: $0

4. Table formatting:
   - Enable row numbers
   - Set pagination: 20 rows per page
   - Enable column sorting
   - Color by value for Average Price column

5. Name: "Neighborhood Statistics Detail"
6. **Save and return**

### Step 6: Visualization 5 - Price Trends Line Chart

**Purpose**: Show how prices vary within neighborhoods

1. **Create visualization** → **Lens**
2. Chart type: **Line**
3. Configuration:
   - Horizontal axis: `neighborhood_id` (Top 10)
   - Vertical axis: Multiple metrics:
     - Min of `listing_price` (blue line)
     - Average of `listing_price` (green line) 
     - Max of `listing_price` (red line)
4. Display settings:
   - Show data points: Yes
   - Curve type: Linear
   - Missing values: Don't show
5. Name: "Price Ranges by Neighborhood"
6. **Save and return**

### Step 7: Add Interactive Filters

1. Click **Add filter** → **Add control**
2. Add these controls:
   
   **Price Range Slider**:
   - Field: `listing_price`
   - Control type: Range slider
   - Step: 50000
   
   **Property Type Dropdown**:
   - Field: `property_type`
   - Control type: Options list
   - Allow multiple selections: Yes
   
   **Bedrooms Selector**:
   - Field: `bedrooms`
   - Control type: Options list
   
   **Square Feet Range**:
   - Field: `square_feet`
   - Control type: Range slider

3. Position controls at the top of dashboard

### Step 8: Dashboard Layout

Arrange your visualizations thoughtfully:

```
┌─────────────────────────────────────────────────────┐
│                    CONTROLS BAR                     │
├───────────────────┬─────────────────────────────────┤
│                   │                                 │
│    MAP VIEW       │   AVG PRICE BAR CHART          │
│    (40% width)    │   (60% width)                  │
│                   │                                 │
├───────────────────┼─────────────────────────────────┤
│  DONUT CHART      │   PRICE TRENDS LINE CHART      │
│  (30% width)      │   (70% width)                  │
├───────────────────┴─────────────────────────────────┤
│          DETAILED STATISTICS TABLE                  │
│                 (Full width)                        │
└─────────────────────────────────────────────────────┘
```

### Step 9: Finishing Touches

1. **Add a title markdown panel**:
   - Click **Create visualization** → **Text**
   - Add markdown:
   ```markdown
   # 🏘️ Neighborhood Real Estate Analytics Dashboard
   
   Comprehensive analysis of property markets across neighborhoods.
   Last updated: {current_date}
   
   **Key Metrics**: {total_properties} properties | ${avg_price} average
   ```

2. **Set refresh interval**:
   - Click time picker → **Refresh every** → 30 seconds

3. **Save dashboard**:
   - Click **Save** → Give it a description
   - Enable **Store time with dashboard**

## Dashboard 2: Price Distribution Analysis (Demo 5)

This dashboard focuses on price distribution patterns and market segmentation.

### Vision for This Dashboard

Create a market analysis dashboard featuring:
- Price distribution histogram
- Percentile analysis
- Property type comparisons
- Market segment deep-dives

### Prerequisites: Price Analysis Data View

1. Go to **Stack Management** → **Data Views**
2. Create or modify the `Real Estate Properties` data view
3. Add **Runtime Fields** for market segmentation:
   
   **Market Segment Field**:
   - Name: `market_segment`
   - Type: `keyword`
   - Script:
   ```painless
   double price = doc['listing_price'].value;
   if (price < 500000) {
     emit('Budget');
   } else if (price < 1000000) {
     emit('Mid-Market');
   } else if (price < 1500000) {
     emit('Upper-Mid');
   } else {
     emit('Luxury');
   }
   ```
   
   **Price Range Field** (for bucketing):
   - Name: `price_range_100k`
   - Type: `keyword`
   - Script:
   ```painless
   long bucket = Math.floor(doc['listing_price'].value / 100000);
   long lower = bucket * 100;
   long upper = (bucket + 1) * 100;
   emit('$' + lower + 'k-$' + upper + 'k');
   ```

### Step 1: Create New Dashboard

1. Navigate to **Analytics** → **Dashboard**
2. Click **Create dashboard**
3. Name: "Real Estate Price Distribution Analysis"

### Step 2: Visualization 1 - Price Distribution Histogram

**Purpose**: Replicate Demo 5's price histogram

**Data View Required**: `Real Estate Properties` (with runtime fields)

1. **Create visualization** → **Lens**
2. Chart type: **Bar vertical stacked**
3. Configuration:
   - **Horizontal axis**: 
     - Field: `listing_price`
     - Function: **Intervals**
     - Interval: `100000`
     - Extended bounds:
       - Min: `0`
       - Max: `2000000`
   - **Vertical axis**: 
     - Function: **Count**
     - Display name: "Number of Properties"

4. Advanced Configuration:
   - Click gear icon on horizontal axis
   - **Value format**: Custom format string: `$0,0`
   - **Axis title**: "Price Range"
   - **Label rotation**: 45 degrees (if labels overlap)

5. Styling:
   - **Chart settings** (right panel):
     - Value labels: Show
     - Legend: Hide
     - Tooltip: Show stacked value
   - **Color mapping**:
     - Single color or gradient
     - Use green-yellow-red for visual impact

6. Name: "Price Distribution ($100k buckets)"
7. **Save and return**

**Alternative: Using Runtime Field**
Instead of intervals, use the `price_range_100k` runtime field:
1. Horizontal axis: `price_range_100k` (Top values, 20)
2. This provides pre-formatted labels like "$500k-$600k"

### Step 3: Visualization 2 - Price Percentiles Gauge

**Purpose**: Show market percentiles at a glance

1. **Create visualization** → **Lens**
2. Chart type: **Metric**
3. Create multiple metrics:
   
   **25th Percentile**:
   - Function: Percentile of `listing_price`
   - Percentile: 25
   - Format: $0,0
   - Color: Blue
   
   **Median (50th)**:
   - Function: Percentile of `listing_price`
   - Percentile: 50
   - Format: $0,0
   - Color: Green
   
   **75th Percentile**:
   - Function: Percentile of `listing_price`
   - Percentile: 75
   - Format: $0,0
   - Color: Orange
   
   **95th Percentile**:
   - Function: Percentile of `listing_price`
   - Percentile: 95
   - Format: $0,0
   - Color: Red

4. Layout: Horizontal layout
5. Name: "Market Price Percentiles"
6. **Save and return**

### Step 4: Visualization 3 - Property Type Comparison

**Purpose**: Compare statistics across property types

1. **Create visualization** → **Lens**
2. Change to **Table**
3. Structure:
   
   **Rows**: `property_type` (Top values, all)
   
   **Columns**:
   - Count (labeled "Total Properties")
   - Average of `listing_price` (labeled "Avg Price")
   - Min of `listing_price` (labeled "Min Price")
   - Max of `listing_price` (labeled "Max Price")
   - Standard deviation of `listing_price` (labeled "Price Volatility")

4. Formatting:
   - Apply currency format to price columns
   - Color code by average price
   - Sort by Count descending

5. Name: "Statistics by Property Type"
6. **Save and return**

### Step 5: Visualization 4 - Box Plot for Price Ranges

**Purpose**: Professional statistical visualization

1. **Create visualization** → **Custom visualization**
2. If box plot not available, create manually with **Lens**:
   - Chart type: **Bar horizontal**
   - For each property type, show:
     - Min (thin bar)
     - 25th percentile (thick bar start)
     - Median (marker)
     - 75th percentile (thick bar end)
     - Max (thin bar)
     - Outliers as points

3. Alternative approach using **Area chart**:
   - X-axis: `property_type`
   - Y-axis bands:
     - Min to 25th percentile (light shade)
     - 25th to 75th percentile (dark shade)
     - 75th to Max (light shade)
   - Median as line overlay

4. Name: "Price Distribution by Property Type"
5. **Save and return**

### Step 6: Visualization 5 - Cumulative Distribution Function

**Data View Required**: `Real Estate Properties`

**Purpose**: Show what percentage of properties fall below each price point

1. **Create visualization** → **Lens**
2. Chart type: **Line**
3. Configuration:
   - X-axis: `listing_price` (intervals of 100000)
   - Y-axis: Cumulative sum of Count
   - Normalize to percentage

4. Add reference lines:
   - $500k (budget buyers)
   - $1M (mid-market)
   - $1.5M (luxury threshold)

5. Styling:
   - Smooth curve
   - Area fill below line
   - Show grid lines

6. Name: "Cumulative Price Distribution"
7. **Save and return**

### Step 7: Visualization 6 - Market Segments Pie Chart

**Purpose**: Categorize properties into market segments

**Data View Required**: `Real Estate Properties` (with `market_segment` runtime field)

1. **Create visualization** → **Lens**
2. Chart type: **Pie** (or **Donut** for modern look)
3. Configuration:
   - **Slice by**: `market_segment` (runtime field created earlier)
   - **Size by**: Count of records
   - **Number of slices**: 4 (all segments)

4. Display settings:
   - **Values in legend**: Show
   - **Label position**: Inside or outside
   - **Percentage**: Show
   - **Decimal places**: 1

5. Color configuration:
   - Manually assign colors:
     - Budget: Green (#4CAF50)
     - Mid-Market: Blue (#2196F3)
     - Upper-Mid: Orange (#FF9800)
     - Luxury: Purple (#9C27B0)

6. Name: "Market Segmentation"
7. **Save and return**

### Step 8: Visualization 7 - Heat Map

**Data View Required**: `Real Estate Properties`

**Purpose**: Show price correlation with bedrooms and square feet

1. **Create visualization** → **Lens**
2. Chart type: **Heat map**
3. Configuration:
   - X-axis: `bedrooms` (all values)
   - Y-axis: `square_feet` (intervals of 500)
   - Cell color: Average of `listing_price`
   - Color palette: Cool to warm

4. Interactivity:
   - Show tooltip with exact values
   - Click to filter dashboard

5. Name: "Price Heat Map (Beds vs Sq Ft)"
6. **Save and return**

### Step 9: Dashboard Layout

Optimal arrangement for price analysis:

```
┌─────────────────────────────────────────────────────┐
│              MARKET PRICE PERCENTILES               │
│                   (metrics row)                     │
├─────────────────────┬───────────────────────────────┤
│                     │                               │
│  PRICE HISTOGRAM    │   CUMULATIVE DISTRIBUTION    │
│     (50% width)     │       (50% width)            │
│                     │                               │
├─────────────────────┼───────────────────────────────┤
│   MARKET SEGMENTS   │   PRICE BOX PLOTS            │
│    PIE CHART        │   BY PROPERTY TYPE           │
│    (40% width)      │     (60% width)              │
├─────────────────────┴───────────────────────────────┤
│          STATISTICS BY PROPERTY TYPE TABLE          │
│                    (full width)                     │
├─────────────────────────────────────────────────────┤
│              PRICE HEAT MAP                         │
│          (Bedrooms vs Square Feet)                  │
└─────────────────────────────────────────────────────┘
```

## Creating Additional Data Views for Analysis

### Property Type Data View

For property type-specific analysis:

1. **Create Data View**:
   - Name: `Properties by Type`
   - Index pattern: `properties*`
   - Add filter: `property_type: *` (excludes null values)

2. **Add Calculated Fields**:
   - `value_score`: Rate properties based on price/sqft ratio
   - `size_category`: Small/Medium/Large based on square feet
   - `bedroom_category`: Studio/1BR/2BR/3BR+

### Time-Based Data View

If your data includes listing dates:

1. **Create Data View**:
   - Name: `Property Listings Timeline`
   - Index pattern: `properties*`
   - Time field: `listing_date` or `@timestamp`

2. **Time-based visualizations**:
   - New listings per week/month
   - Price trends over time
   - Seasonal patterns

## Region Map vs Choropleth: When to Use Each

### Region Map (Deprecated in newer versions)

**Use when**:
- Working with Kibana < 7.14
- Simple boundary matching needed
- Limited to predefined EMS boundaries

**Configuration**:
- Requires exact field matching with boundary names
- Limited styling options
- Single metric display

### Choropleth Map (Recommended)

**Use when**:
- Need custom boundaries (neighborhoods)
- Multiple metrics per region
- Advanced styling required
- Kibana 7.14+

**Configuration for Neighborhoods**:

1. **Prepare GeoJSON boundaries**:
   ```json
   {
     "type": "FeatureCollection",
     "features": [
       {
         "type": "Feature",
         "properties": {
           "neighborhood_id": "SOMA",
           "name": "South of Market"
         },
         "geometry": {
           "type": "Polygon",
           "coordinates": [[[...]]]]
         }
       }
     ]
   }
   ```

2. **Upload to Kibana**:
   - Maps → Add layer → Upload GeoJSON
   - Or configure in kibana.yml:
   ```yaml
   map.regionmap:
     layers:
       - name: "SF Neighborhoods"
         url: "https://your-server/neighborhoods.geojson"
         fields:
           - name: "neighborhood_id"
             description: "Neighborhood ID"
   ```

3. **Join configuration**:
   - Boundaries join field: `neighborhood_id` (from GeoJSON)
   - Data join field: `neighborhood_id.keyword` (from index)
   - Metrics: Average price, Count, etc.

## Advanced Dashboard Techniques

### Creating Drill-Down Functionality

1. **Configure visualization interactions**:
   - Edit any visualization
   - Under "Settings" → "Interactions"
   - Enable "Use as filter"
   - Now clicking elements filters the entire dashboard

2. **Create navigation between dashboards**:
   ```markdown
   // In a Markdown visualization
   [View Neighborhood Details](/app/dashboards/neighborhood-dashboard)
   [Analyze Price Distribution](/app/dashboards/price-dashboard)
   ```

### Adding Dynamic Text Panels

Create informative text panels that update with data:

1. **Create visualization** → **Text**
2. Use Elasticsearch SQL to fetch metrics:
   ```sql
   POST /_sql?format=txt
   {
     "query": "SELECT COUNT(*) as total, AVG(listing_price) as avg_price FROM properties"
   }
   ```
3. Embed results in markdown

### Time-Based Analysis

If your data includes timestamps:

1. **Add time filter**:
   - Set your Data View timestamp field
   - Use time picker in dashboard
   - Create date histograms for trend analysis

2. **Animated visualizations**:
   - Use "Play" button on time picker
   - Watch market evolution over time

### Custom Color Schemes

Create branded visualizations:

1. Navigate to **Stack Management** → **Advanced Settings**
2. Find "Visualization colors"
3. Define custom palette:
   ```json
   {
     "palette": [
       "#1E88E5",  // Primary blue
       "#43A047",  // Success green
       "#FB8C00",  // Warning orange
       "#E53935"   // Danger red
     ]
   }
   ```

### Performance Optimization

For smooth dashboards with large datasets:

1. **Use saved searches**:
   - Pre-filter data in Discover
   - Save search
   - Base visualizations on saved search

2. **Implement sampling**:
   ```json
   // In visualization query
   {
     "aggs": {
       "sample": {
         "sampler": {
           "shard_size": 200
         },
         "aggs": {
           // Your actual aggregation
         }
       }
     }
   }
   ```

3. **Cache queries**:
   - Enable query cache in Elasticsearch
   - Set appropriate refresh intervals

## Data View Best Practices

### Organizing Multiple Data Views

1. **Naming Convention**:
   - `[Domain] - [Purpose]`: "Real Estate - Neighborhoods"
   - `[Index] - [View Type]`: "properties - Aggregated"
   - Include version if needed: "Properties v2"

2. **Field Management**:
   - Hide unused fields to improve performance
   - Format fields appropriately (currency, percentages)
   - Add field descriptions for clarity

3. **Runtime Fields vs Scripted Fields**:
   - Use **Runtime Fields** (Kibana 7.11+):
     - Calculated at query time
     - More flexible and powerful
     - Better performance for large datasets
   - Avoid **Scripted Fields** (deprecated):
     - Legacy feature
     - Performance issues
     - Limited functionality

4. **Index Pattern Strategy**:
   - Use wildcards for future-proofing: `properties*`
   - Separate data views for different use cases
   - Consider data view permissions for multi-tenant setups

### Optimizing Map Visualizations

1. **For Neighborhood Analysis**:
   - Aggregate at index time when possible
   - Use doc_count for better performance
   - Limit top values to reasonable number (10-20)

2. **Boundary Optimization**:
   - Simplify GeoJSON geometries
   - Use appropriate precision levels
   - Host boundaries on same domain (avoid CORS)

3. **Performance Tips**:
   - Enable browser caching for GeoJSON
   - Use grid aggregation for large datasets
   - Set appropriate zoom constraints

## Best Practices

### Design Principles

1. **Visual Hierarchy**:
   - Most important metrics at top
   - Use size to indicate importance
   - Group related visualizations

2. **Color Consistency**:
   - Use same color for same metric across charts
   - Red for warnings/high values
   - Green for good/low values
   - Blue for neutral information

3. **Information Density**:
   - Balance detail with clarity
   - Use progressive disclosure
   - Start with overview, allow drill-down

4. **Responsive Design**:
   - Test on different screen sizes
   - Use auto-scaling options
   - Consider mobile viewers

### Data Accuracy

1. **Verify aggregations**:
   ```bash
   # Compare Kibana results with direct query
   curl -X POST "localhost:9200/properties/_search" -H 'Content-Type: application/json' -d'
   {
     "aggs": {
       "avg_price": {
         "avg": {
           "field": "listing_price"
         }
       }
     }
   }'
   ```

2. **Handle missing data**:
   - Set "missing" values handling
   - Use null_value in mappings
   - Document data quality issues

3. **Time zones**:
   - Set correct timezone in Kibana
   - Align with data source timezone
   - Document timezone assumptions

### User Experience

1. **Interactive elements**:
   - Add clear filter controls
   - Enable click-to-filter
   - Provide reset button

2. **Loading indicators**:
   - Show query time
   - Add loading spinners
   - Cache slow queries

3. **Help text**:
   - Add descriptions to complex visualizations
   - Include data definitions
   - Provide contact for questions

4. **Export capabilities**:
   - Enable PDF reports
   - Allow CSV data export
   - Share dashboard links

## Troubleshooting

### Common Issues and Solutions

#### Issue: "Data view does not contain any geospatial fields"
**Solution**:
1. Check field mapping in Stack Management → Data Views
2. Ensure location field is mapped as `geo_point`:
   ```json
   PUT /properties/_mapping
   {
     "properties": {
       "location": {
         "type": "geo_point"
       }
     }
   }
   ```
3. If data is already indexed, create a runtime field:
   ```painless
   if (doc['latitude'].size() > 0 && doc['longitude'].size() > 0) {
     emit(doc['latitude'].value, doc['longitude'].value);
   }
   ```

#### Issue: "Choropleth map shows no data"
**Solution**:
1. Verify join fields match exactly (check for .keyword suffix)
2. Ensure GeoJSON property names match your data
3. Check boundaries are valid GeoJSON
4. Test with smaller dataset first
5. Enable browser console to see join errors

#### Issue: "No data found in visualization"
**Solution**:
1. Check Data View matches index pattern
2. Verify time range includes your data
3. Remove all filters and try again
4. Check field mappings in Stack Management

#### Issue: Visualizations loading slowly
**Solution**:
1. Reduce time range
2. Add sampling to aggregations
3. Increase Elasticsearch heap memory
4. Use saved searches with pre-filters

#### Issue: Incorrect aggregation results
**Solution**:
1. Check field data type (must be numeric for math)
2. Verify no filters are applied
3. Look for null/missing values
4. Compare with direct Elasticsearch query

#### Issue: Dashboard won't save
**Solution**:
1. Check Kibana permissions
2. Reduce dashboard size (too many visualizations)
3. Clear browser cache
4. Check Kibana logs for errors

#### Issue: Colors not showing correctly
**Solution**:
1. Verify data ranges for color rules
2. Check color blind mode isn't enabled
3. Reset to default palette
4. Clear visualization cache

### Query Debugging

Enable query inspection:
1. Click "Inspect" on any visualization
2. View "Request" tab for Elasticsearch query
3. View "Response" tab for raw data
4. Copy query to Dev Tools for testing

Example debug query:
```json
GET properties/_search
{
  "size": 0,
  "query": {
    "match_all": {}
  },
  "aggs": {
    "neighborhoods": {
      "terms": {
        "field": "neighborhood_id.keyword",
        "size": 20
      },
      "aggs": {
        "avg_price": {
          "avg": {
            "field": "listing_price"
          }
        }
      }
    }
  }
}
```

### Performance Monitoring

Track dashboard performance:
1. Open browser Developer Tools
2. Go to Network tab
3. Look for slow requests (>1s)
4. Optimize those specific visualizations

### Getting Help

Resources for additional help:
1. **Elastic Documentation**: https://www.elastic.co/guide/en/kibana/current/index.html
2. **Community Forums**: https://discuss.elastic.co/c/kibana
3. **Video Tutorials**: Elastic's YouTube channel
4. **Local Kibana Dev Tools**: http://localhost:5601/app/dev_tools

## Conclusion

You now have two professional-grade dashboards that provide deep insights into your real estate data:

1. **Neighborhood Statistics Dashboard**: Perfect for comparing markets and identifying opportunities
2. **Price Distribution Dashboard**: Essential for understanding market dynamics and segmentation

### Next Steps

1. **Customize for your needs**:
   - Add your company branding
   - Include additional data sources
   - Create role-based versions

2. **Automate reporting**:
   - Set up scheduled PDF reports
   - Configure alerts for market changes
   - Create weekly summary emails

3. **Expand analysis**:
   - Add time-based trending
   - Include external data (crime, schools, etc.)
   - Build predictive models

4. **Share with stakeholders**:
   - Create read-only dashboard links
   - Embed in company portal
   - Present in meetings

Remember: Great dashboards tell a story. Start with the big picture, allow users to explore details, and always maintain data accuracy and visual clarity.

Happy dashboarding! 🎨📊