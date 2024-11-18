# Emissions Tracking API Documentation

## Base URL

All URLs referenced in the documentation have the following base:
`http://localhost:8000/api/`

## Endpoints

### API Root
- URL: `/`
- Method: GET
- Description: Provides an overview of available endpoints

### Reports

#### List all reports
- URL: `/reports/`
- Method: GET
- Response: List of all reports

#### Create a new report
- URL: `/reports/`
- Method: POST
- Data Params: 
  ```json
  {
    "name": "Report Name",
    "date": "YYYY-MM-DD"
  }
  ```
- Response: Created report object

#### Get a specific report
- URL: `/reports/{id}/`
- Method: GET
- Response: Report details

#### Update a report
- URL: `/reports/{id}/`
- Method: PUT
- Data Params: Same as POST
- Response: Updated report object

#### Delete a report
- URL: `/reports/{id}/`
- Method: DELETE
- Response: 204 No Content

#### Get sources for a report
- URL: `/reports/{id}/sources/`
- Method: GET
- Response: List of sources associated with the report

#### Get projected emissions for a report
- URL: `/reports/{id}/projected-emissions/`
- Method: GET
- Query Params:
  - year (optional): The year for which to project emissions
  - strategies (optional): List of strategy IDs to apply
- Response: Projected emissions data
- Note: Calculations are performed using NumPy for efficiency, and results are returned as Decimal values for precision.

#### Add a reduction strategy to a report
- URL: `/reports/{id}/add-strategy/`
- Method: POST
- Data Params:
  ```json
  {
    "strategy_id": strategy_id
  }
  ```
- Response: Status message

#### Remove a reduction strategy from a report
- URL: `/reports/{id}/remove-strategy/`
- Method: POST
- Data Params:
  ```json
  {
    "strategy_id": strategy_id
  }
  ```
- Response: Status message

### Sources

#### List all sources
- URL: `/sources/`
- Method: GET
- Response: List of all sources

#### Create a new source
- URL: `/sources/`
- Method: POST
- Data Params:
  ```json
  {
    "name": "Source Name",
    "report": report_id,
    "category": "TRANSPORT",
    "description": "Description",
    "method": "DISTANCE",
    "emission_factor": "0.1",
    "value": "1000.00",
    "value_unit": "km",
    "quantity": 1,
    "lifetime": 5,
    "acquisition_year": 2023,
    "uncertainty": "5.00",
    "year": null
  }
  ```
- Response: Created source object
- Note: Numeric values should be provided as strings to ensure Decimal precision.

#### Get a specific source
- URL: `/sources/{id}/`
- Method: GET
- Response: Source details

#### Update a source
- URL: `/sources/{id}/`
- Method: PUT
- Data Params: Same as POST
- Response: Updated source object

#### Delete a source
- URL: `/sources/{id}/`
- Method: DELETE
- Response: 204 No Content

#### Get emissions by year for a source
- URL: `/sources/{id}/emissions-by-year/`
- Method: GET
- Query Params: 
  - start_year (optional)
  - end_year (optional)
- Response: Emissions data for each year

#### Get total emission for a source
- URL: `/sources/{id}/total-emission/`
- Method: GET
- Response: Total emission value

#### Get modifications for a source
- URL: `/sources/{id}/modifications/`
- Method: GET
- Response: List of modifications associated with the source

### Reduction Strategies

#### List all reduction strategies
- URL: `/reduction-strategies/`
- Method: GET
- Response: List of all reduction strategies

#### Create a new reduction strategy
- URL: `/reduction-strategies/`
- Method: POST
- Data Params:
  ```json
  {
    "name": "Strategy Name"
  }
  ```
- Response: Created reduction strategy object

#### Get a specific reduction strategy
- URL: `/reduction-strategies/{id}/`
- Method: GET
- Response: Reduction strategy details

#### Update a reduction strategy
- URL: `/reduction-strategies/{id}/`
- Method: PUT
- Data Params: Same as POST
- Response: Updated reduction strategy object

#### Delete a reduction strategy
- URL: `/reduction-strategies/{id}/`
- Method: DELETE
- Response: 204 No Content

#### Get total reduction for a strategy
- URL: `/reduction-strategies/{id}/total-reduction/`
- Method: GET
- Query Params:
  - start_year (optional)
  - end_year (optional)
- Response: Total reduction data

#### Get modifications for a strategy
- URL: `/reduction-strategies/{id}/modifications/`
- Method: GET
- Response: List of modifications associated with the strategy

### Modifications

#### List all modifications
- URL: `/modifications/`
- Method: GET
- Response: List of all modifications

#### Create a new modification
- URL: `/modifications/`
- Method: POST
- Data Params:
  ```json
  {
    "reduction_strategy": strategy_id,
    "source": source_id,
    "modification_type": "VALUE",
    "value": 0.9,
    "order": 1,
    "start_year": 2023,
    "end_year": null,
    "is_progressive": false,
    "target_value": null
  }
  ```
- Response: Created modification object

#### Get a specific modification
- URL: `/modifications/{id}/`
- Method: GET
- Response: Modification details

#### Update a modification
- URL: `/modifications/{id}/`
- Method: PUT
- Data Params: Same as POST
- Response: Updated modification object

#### Delete a modification
- URL: `/modifications/{id}/`
- Method: DELETE
- Response: 204 No Content

### Projections

#### Project modifications
- URL: `/projections/project_modifications/`
- Method: POST
- Data Params:
  ```json
  {
    "source_id": source_id,
    "modification_ids": [mod_id1, mod_id2],
    "start_year": 2023,
    "end_year": 2030
  }
  ```
- Response: Projected emissions data
- Note: Calculations are performed using vectorized operations for improved performance.

### Dashboard
- URL: `/dashboard/`
- Method: GET
- Description: Renders the dashboard view and calculate emissions based on a range of years.