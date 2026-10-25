# German Economics Dataset
[![CI](https://github.com/kleinnconrad/dataset.economics.germany/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/kleinnconrad/dataset.economics.germany/actions/workflows/ci.yml)

A dataset of the German economy for economic analysis and prediction. A pipeline in GitHub Actions runs twice a week (Tuesdays and Fridays) for at most 30 minutes. It collects statistical series (GDP, prices and inflation, interest rates, commodity prices, electricity, labour market, production, surveys including shortages), the public attention to large companies, and the economic news of German outlets and the press releases of economic institutions and companies. It labels the news and press releases with Google Gemini (`gemini-2.5-flash`) and stores everything as partitioned JSON files in this repository. Statistical series are stored as vintages, so that every past state of a revised series can be reconstructed.

## Table of Contents
- [Dataset Overview](#dataset-overview)
- [Datasets](#datasets)
  - [Statistical Series and Vintages](#statistical-series-and-vintages)
  - [News Items and Press Releases](#news-items-and-press-releases)
- [Correlation with Other Datasets](#correlation-with-other-datasets)
- [Data Model](#data-model)
- [Example Records](#example-records)
- [Sources and Fetch Rules](#sources-and-fetch-rules)
- [Pipeline](#pipeline)
- [Data Files](#data-files)
- [Workflows](#workflows)
- [Configuration](#configuration)
- [Running Locally](#running-locally)
- [Continuous Integration](#continuous-integration)
- [Setup](#setup)
- [Sources and Attribution](#sources-and-attribution)

## Dataset Overview
<!-- DATASET_OVERVIEW_START -->
**Last updated:** 2026-10-25 15:24 UTC

| Dataset | Records | Items | Files | Observed | Content |
|---|---|---|---|---|---|
| `economic_series` | 0 | 0 | 0 | none | A vintage of a statistical series: all values at the first observation, then the added, revised and removed periods. |
| `series_catalog` | 0 | 0 | 0 | none | An entry of the series catalog, recorded when it appears or changes. |
| `news_items` | 0 | 0 | 0 | none | Metadata of one news article. The text is not stored. |
| `press_releases` | 0 | 0 | 0 | none | Metadata of one press release. The text is not stored. |
| `text_annotations` | 0 | 0 | 0 | none | Gemini labels of one news article or press release. |
| `companies` | 0 | 0 | 0 | none | An entry of the company registry, recorded when it appears or changes. |
| `wikipedia_pageviews` | 0 | 0 | 0 | none | Daily views of the German Wikipedia article of a registered company. |

**Runs**

- No run yet.

**Statistical series**

- **Active series:** 238 (eurostat 143, worldbank_cmo 35, ecb 27, bundesbank 19, smard 14); with stored values: 0

<details>
<summary>Series: latest period and number of revisions</summary>

| Series | Topic | Frequency | Unit | First period | Latest period | Periods | Revisions |
|---|---|---|---|---|---|---|---|
| `bankruptcy_declarations_index.DE` | business demography | M | index, 2021 = 100 | none | none | 0 | 0 |
| `business_registrations_index.DE` | business demography | M | index, 2021 = 100 | none | none | 0 | 0 |
| `aluminium_price.WLD` | commodities | M | US dollar per metric ton | none | none | 0 | 0 |
| `brent_crude_oil_price.WLD` | commodities | M | US dollar per barrel | none | none | 0 | 0 |
| `coal_australia_price.WLD` | commodities | M | US dollar per metric ton | none | none | 0 | 0 |
| `cocoa_price.WLD` | commodities | M | US dollar per kilogram | none | none | 0 | 0 |
| `coffee_arabica_price.WLD` | commodities | M | US dollar per kilogram | none | none | 0 | 0 |
| `commodity_price_index_agriculture.WLD` | commodities | M | index, 2010 = 100 (nominal US dollars) | none | none | 0 | 0 |
| `commodity_price_index_base_metals.WLD` | commodities | M | index, 2010 = 100 (nominal US dollars) | none | none | 0 | 0 |
| `commodity_price_index_energy.WLD` | commodities | M | index, 2010 = 100 (nominal US dollars) | none | none | 0 | 0 |
| `commodity_price_index_fertilizers.WLD` | commodities | M | index, 2010 = 100 (nominal US dollars) | none | none | 0 | 0 |
| `commodity_price_index_food.WLD` | commodities | M | index, 2010 = 100 (nominal US dollars) | none | none | 0 | 0 |
| `commodity_price_index_metals_minerals.WLD` | commodities | M | index, 2010 = 100 (nominal US dollars) | none | none | 0 | 0 |
| `commodity_price_index_non_energy.WLD` | commodities | M | index, 2010 = 100 (nominal US dollars) | none | none | 0 | 0 |
| `commodity_price_index_precious_metals.WLD` | commodities | M | index, 2010 = 100 (nominal US dollars) | none | none | 0 | 0 |
| `commodity_price_index_total.WLD` | commodities | M | index, 2010 = 100 (nominal US dollars) | none | none | 0 | 0 |
| `copper_price.WLD` | commodities | M | US dollar per metric ton | none | none | 0 | 0 |
| `cotton_price.WLD` | commodities | M | US dollar per kilogram | none | none | 0 | 0 |
| `crude_oil_average_price.WLD` | commodities | M | US dollar per barrel | none | none | 0 | 0 |
| `dap_fertilizer_price.WLD` | commodities | M | US dollar per metric ton | none | none | 0 | 0 |
| `gold_price.WLD` | commodities | M | US dollar per troy ounce | none | none | 0 | 0 |
| `iron_ore_price.WLD` | commodities | M | US dollar per dry metric ton unit | none | none | 0 | 0 |
| `lead_price.WLD` | commodities | M | US dollar per metric ton | none | none | 0 | 0 |
| `maize_price.WLD` | commodities | M | US dollar per metric ton | none | none | 0 | 0 |
| `natural_gas_europe_price.WLD` | commodities | M | US dollar per million British thermal units | none | none | 0 | 0 |
| `natural_gas_us_price.WLD` | commodities | M | US dollar per million British thermal units | none | none | 0 | 0 |
| `nickel_price.WLD` | commodities | M | US dollar per metric ton | none | none | 0 | 0 |
| `palm_oil_price.WLD` | commodities | M | US dollar per metric ton | none | none | 0 | 0 |
| `platinum_price.WLD` | commodities | M | US dollar per troy ounce | none | none | 0 | 0 |
| `potassium_chloride_price.WLD` | commodities | M | US dollar per metric ton | none | none | 0 | 0 |
| `silver_price.WLD` | commodities | M | US dollar per troy ounce | none | none | 0 | 0 |
| `soybeans_price.WLD` | commodities | M | US dollar per metric ton | none | none | 0 | 0 |
| `sugar_world_price.WLD` | commodities | M | US dollar per kilogram | none | none | 0 | 0 |
| `tin_price.WLD` | commodities | M | US dollar per metric ton | none | none | 0 | 0 |
| `urea_price.WLD` | commodities | M | US dollar per metric ton | none | none | 0 | 0 |
| `wheat_price.WLD` | commodities | M | US dollar per metric ton | none | none | 0 | 0 |
| `zinc_price.WLD` | commodities | M | US dollar per metric ton | none | none | 0 | 0 |
| `day_ahead_power_price.DE` | energy | D | euro per MWh | none | none | 0 | 0 |
| `grid_load.DE` | energy | D | MWh per day | none | none | 0 | 0 |
| `power_generation_biomass.DE` | energy | D | MWh per day | none | none | 0 | 0 |
| `power_generation_hard_coal.DE` | energy | D | MWh per day | none | none | 0 | 0 |
| `power_generation_hydro.DE` | energy | D | MWh per day | none | none | 0 | 0 |
| `power_generation_lignite.DE` | energy | D | MWh per day | none | none | 0 | 0 |
| `power_generation_natural_gas.DE` | energy | D | MWh per day | none | none | 0 | 0 |
| `power_generation_other_conventional.DE` | energy | D | MWh per day | none | none | 0 | 0 |
| `power_generation_other_renewable.DE` | energy | D | MWh per day | none | none | 0 | 0 |
| `power_generation_pumped_storage.DE` | energy | D | MWh per day | none | none | 0 | 0 |
| `power_generation_solar.DE` | energy | D | MWh per day | none | none | 0 | 0 |
| `power_generation_wind_offshore.DE` | energy | D | MWh per day | none | none | 0 | 0 |
| `power_generation_wind_onshore.DE` | energy | D | MWh per day | none | none | 0 | 0 |
| `residual_load.DE` | energy | D | MWh per day | none | none | 0 | 0 |
| `eur_chf.EA` | exchange rates | D | Swiss franc per euro | none | none | 0 | 0 |
| `eur_cny.EA` | exchange rates | D | yuan renminbi per euro | none | none | 0 | 0 |
| `eur_gbp.EA` | exchange rates | D | pound sterling per euro | none | none | 0 | 0 |
| `eur_jpy.EA` | exchange rates | D | yen per euro | none | none | 0 | 0 |
| `eur_usd.EA` | exchange rates | D | US dollar per euro | none | none | 0 | 0 |
| `systemic_stress_index.DE` | financial stress | D | index (0 to 1) | none | none | 0 | 0 |
| `systemic_stress_index.EA` | financial stress | D | index (0 to 1) | none | none | 0 | 0 |
| `truck_toll_mileage_index.DE` | high frequency activity | D | index, 2021 = 100 | none | none | 0 | 0 |
| `weekly_activity_index.DE` | high frequency activity | W | percent | none | none | 0 | 0 |
| `house_price_index.DE` | housing | Q | index, 2015 = 100 | none | none | 0 | 0 |
| `house_prices_yoy.DE` | housing | Q | percent change on the same quarter of the previous year | none | none | 0 | 0 |
| `house_prices_yoy.EA` | housing | Q | percent change on the same quarter of the previous year | none | none | 0 | 0 |
| `bund_yield_10y.DE` | interest rates | D | percent per annum | none | none | 0 | 0 |
| `bund_yield_2y.DE` | interest rates | D | percent per annum | none | none | 0 | 0 |
| `bund_yield_30y.DE` | interest rates | D | percent per annum | none | none | 0 | 0 |
| `bund_yield_5y.DE` | interest rates | D | percent per annum | none | none | 0 | 0 |
| `corporate_loan_rate_new_business.DE` | interest rates | M | percent per annum | none | none | 0 | 0 |
| `corporate_loan_rate_new_business.EA` | interest rates | M | percent per annum | none | none | 0 | 0 |
| `ecb_deposit_facility_rate.EA` | interest rates | D | percent per annum | none | none | 0 | 0 |
| `ecb_main_refinancing_rate.EA` | interest rates | D | percent per annum | none | none | 0 | 0 |
| `ecb_marginal_lending_rate.EA` | interest rates | D | percent per annum | none | none | 0 | 0 |
| `euribor_12m.EA` | interest rates | M | percent per annum | none | none | 0 | 0 |
| `euribor_3m.EA` | interest rates | M | percent per annum | none | none | 0 | 0 |
| `euro_area_aaa_yield_10y.EA` | interest rates | D | percent per annum | none | none | 0 | 0 |
| `euro_area_aaa_yield_2y.EA` | interest rates | D | percent per annum | none | none | 0 | 0 |
| `euro_short_term_rate.EA` | interest rates | D | percent per annum | none | none | 0 | 0 |
| `expected_real_rate_10y.DE` | interest rates | M | percent per annum | none | none | 0 | 0 |
| `long_term_interest_rate.DE` | interest rates | M | percent per annum | none | none | 0 | 0 |
| `long_term_interest_rate.ES` | interest rates | M | percent per annum | none | none | 0 | 0 |
| `long_term_interest_rate.FR` | interest rates | M | percent per annum | none | none | 0 | 0 |
| `long_term_interest_rate.IT` | interest rates | M | percent per annum | none | none | 0 | 0 |
| `long_term_interest_rate.NL` | interest rates | M | percent per annum | none | none | 0 | 0 |
| `mortgage_rate_new_business.DE` | interest rates | M | percent per annum | none | none | 0 | 0 |
| `mortgage_rate_new_business.EA` | interest rates | M | percent per annum | none | none | 0 | 0 |
| `employment_persons.DE` | labour market | M | thousand persons | none | none | 0 | 0 |
| `employment_qoq.DE` | labour market | Q | percent change on the previous quarter | none | none | 0 | 0 |
| `employment_qoq.EA` | labour market | Q | percent change on the previous quarter | none | none | 0 | 0 |
| `job_vacancy_rate.DE` | labour market | Q | percent of occupied and vacant posts | none | none | 0 | 0 |
| `job_vacancy_rate.EA` | labour market | Q | percent of occupied and vacant posts | none | none | 0 | 0 |
| `registered_unemployed.DE` | labour market | M | thousand persons | none | none | 0 | 0 |
| `registered_unemployment_rate.DE` | labour market | M | percent of the civilian labour force | none | none | 0 | 0 |
| `registered_vacancies.DE` | labour market | M | thousand | none | none | 0 | 0 |
| `short_time_workers.DE` | labour market | M | persons | none | none | 0 | 0 |
| `unemployment_rate.AT` | labour market | M | percent of the labour force | none | none | 0 | 0 |
| `unemployment_rate.DE` | labour market | M | percent of the labour force | none | none | 0 | 0 |
| `unemployment_rate.EA` | labour market | M | percent of the labour force | none | none | 0 | 0 |
| `unemployment_rate.ES` | labour market | M | percent of the labour force | none | none | 0 | 0 |
| `unemployment_rate.FR` | labour market | M | percent of the labour force | none | none | 0 | 0 |
| `unemployment_rate.IT` | labour market | M | percent of the labour force | none | none | 0 | 0 |
| `unemployment_rate.NL` | labour market | M | percent of the labour force | none | none | 0 | 0 |
| `unemployment_rate.PL` | labour market | M | percent of the labour force | none | none | 0 | 0 |
| `youth_unemployment_rate.DE` | labour market | M | percent of the labour force | none | none | 0 | 0 |
| `youth_unemployment_rate.EA` | labour market | M | percent of the labour force | none | none | 0 | 0 |
| `corporate_loans_growth.DE` | money and credit | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `corporate_loans_growth.EA` | money and credit | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `m3_growth.EA` | money and credit | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `exports_real_qoq.DE` | output and demand | Q | percent change on the previous quarter | none | none | 0 | 0 |
| `fixed_investment_real_qoq.DE` | output and demand | Q | percent change on the previous quarter | none | none | 0 | 0 |
| `gdp_nominal_level.DE` | output and demand | Q | million euro, current prices | none | none | 0 | 0 |
| `gdp_real_level.DE` | output and demand | Q | million euro, chain-linked volumes (2020) | none | none | 0 | 0 |
| `gdp_real_level.EA` | output and demand | Q | million euro, chain-linked volumes (2020) | none | none | 0 | 0 |
| `gdp_real_qoq.AT` | output and demand | Q | percent change on the previous quarter | none | none | 0 | 0 |
| `gdp_real_qoq.DE` | output and demand | Q | percent change on the previous quarter | none | none | 0 | 0 |
| `gdp_real_qoq.EA` | output and demand | Q | percent change on the previous quarter | none | none | 0 | 0 |
| `gdp_real_qoq.ES` | output and demand | Q | percent change on the previous quarter | none | none | 0 | 0 |
| `gdp_real_qoq.FR` | output and demand | Q | percent change on the previous quarter | none | none | 0 | 0 |
| `gdp_real_qoq.IT` | output and demand | Q | percent change on the previous quarter | none | none | 0 | 0 |
| `gdp_real_qoq.NL` | output and demand | Q | percent change on the previous quarter | none | none | 0 | 0 |
| `gdp_real_qoq.PL` | output and demand | Q | percent change on the previous quarter | none | none | 0 | 0 |
| `gdp_real_yoy.AT` | output and demand | Q | percent change on the same quarter of the previous year | none | none | 0 | 0 |
| `gdp_real_yoy.DE` | output and demand | Q | percent change on the same quarter of the previous year | none | none | 0 | 0 |
| `gdp_real_yoy.EA` | output and demand | Q | percent change on the same quarter of the previous year | none | none | 0 | 0 |
| `gdp_real_yoy.ES` | output and demand | Q | percent change on the same quarter of the previous year | none | none | 0 | 0 |
| `gdp_real_yoy.FR` | output and demand | Q | percent change on the same quarter of the previous year | none | none | 0 | 0 |
| `gdp_real_yoy.IT` | output and demand | Q | percent change on the same quarter of the previous year | none | none | 0 | 0 |
| `gdp_real_yoy.NL` | output and demand | Q | percent change on the same quarter of the previous year | none | none | 0 | 0 |
| `gdp_real_yoy.PL` | output and demand | Q | percent change on the same quarter of the previous year | none | none | 0 | 0 |
| `government_consumption_real_qoq.DE` | output and demand | Q | percent change on the previous quarter | none | none | 0 | 0 |
| `household_consumption_real_qoq.DE` | output and demand | Q | percent change on the previous quarter | none | none | 0 | 0 |
| `imports_real_qoq.DE` | output and demand | Q | percent change on the previous quarter | none | none | 0 | 0 |
| `cpi_index.DE` | prices | M | index, 2020 = 100 | none | none | 0 | 0 |
| `cpi_inflation_yoy.DE` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `hicp_core_inflation_yoy.DE` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `hicp_core_inflation_yoy.EA` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `hicp_energy_inflation_yoy.DE` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `hicp_energy_inflation_yoy.EA` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `hicp_food_inflation_yoy.DE` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `hicp_food_inflation_yoy.EA` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `hicp_index.DE` | prices | M | index, 2025 = 100 | none | none | 0 | 0 |
| `hicp_index.EA` | prices | M | index, 2025 = 100 | none | none | 0 | 0 |
| `hicp_inflation_mom.DE` | prices | M | percent change on the previous month | none | none | 0 | 0 |
| `hicp_inflation_mom.EA` | prices | M | percent change on the previous month | none | none | 0 | 0 |
| `hicp_inflation_yoy.AT` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `hicp_inflation_yoy.DE` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `hicp_inflation_yoy.EA` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `hicp_inflation_yoy.ES` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `hicp_inflation_yoy.FR` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `hicp_inflation_yoy.IT` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `hicp_inflation_yoy.NL` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `hicp_inflation_yoy.PL` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `hicp_non_energy_goods_inflation_yoy.DE` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `hicp_non_energy_goods_inflation_yoy.EA` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `hicp_services_inflation_yoy.DE` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `hicp_services_inflation_yoy.EA` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `household_electricity_price.DE` | prices | S | euro per kWh | none | none | 0 | 0 |
| `household_electricity_price.EA` | prices | S | euro per kWh | none | none | 0 | 0 |
| `household_electricity_price.EU27_2020` | prices | S | euro per kWh | none | none | 0 | 0 |
| `household_electricity_price.FR` | prices | S | euro per kWh | none | none | 0 | 0 |
| `household_electricity_price.IT` | prices | S | euro per kWh | none | none | 0 | 0 |
| `household_gas_price.DE` | prices | S | euro per kWh | none | none | 0 | 0 |
| `household_gas_price.EA` | prices | S | euro per kWh | none | none | 0 | 0 |
| `household_gas_price.EU27_2020` | prices | S | euro per kWh | none | none | 0 | 0 |
| `import_prices_energy_yoy.DE` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `import_prices_yoy.DE` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `industrial_electricity_price.DE` | prices | S | euro per kWh | none | none | 0 | 0 |
| `industrial_electricity_price.EA` | prices | S | euro per kWh | none | none | 0 | 0 |
| `industrial_electricity_price.EU27_2020` | prices | S | euro per kWh | none | none | 0 | 0 |
| `industrial_electricity_price.FR` | prices | S | euro per kWh | none | none | 0 | 0 |
| `industrial_electricity_price.IT` | prices | S | euro per kWh | none | none | 0 | 0 |
| `industrial_gas_price.DE` | prices | S | euro per kWh | none | none | 0 | 0 |
| `industrial_gas_price.EA` | prices | S | euro per kWh | none | none | 0 | 0 |
| `industrial_gas_price.EU27_2020` | prices | S | euro per kWh | none | none | 0 | 0 |
| `producer_prices_energy_yoy.DE` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `producer_prices_index.DE` | prices | M | index, 2021 = 100 | none | none | 0 | 0 |
| `producer_prices_yoy.DE` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `producer_prices_yoy.EA` | prices | M | percent change on the same month of the previous year | none | none | 0 | 0 |
| `automotive_production_index.DE` | production and orders | M | index, 2021 = 100 | none | none | 0 | 0 |
| `basic_metals_production_index.DE` | production and orders | M | index, 2021 = 100 | none | none | 0 | 0 |
| `capacity_utilization_industry.DE` | production and orders | Q | percent | none | none | 0 | 0 |
| `capacity_utilization_industry.EA` | production and orders | Q | percent | none | none | 0 | 0 |
| `chemicals_production_index.DE` | production and orders | M | index, 2021 = 100 | none | none | 0 | 0 |
| `construction_production_index.DE` | production and orders | M | index, 2021 = 100 | none | none | 0 | 0 |
| `construction_production_index.EA` | production and orders | M | index, 2021 = 100 | none | none | 0 | 0 |
| `industrial_production_index.DE` | production and orders | M | index, 2021 = 100 | none | none | 0 | 0 |
| `industrial_production_index.EA` | production and orders | M | index, 2021 = 100 | none | none | 0 | 0 |
| `industrial_production_index.FR` | production and orders | M | index, 2021 = 100 | none | none | 0 | 0 |
| `industrial_production_index.IT` | production and orders | M | index, 2021 = 100 | none | none | 0 | 0 |
| `machinery_production_index.DE` | production and orders | M | index, 2021 = 100 | none | none | 0 | 0 |
| `manufacturing_new_orders_domestic_index.DE` | production and orders | M | index, 2021 = 100 | none | none | 0 | 0 |
| `manufacturing_new_orders_ex_large_index.DE` | production and orders | M | index, 2021 = 100 | none | none | 0 | 0 |
| `manufacturing_new_orders_foreign_index.DE` | production and orders | M | index, 2021 = 100 | none | none | 0 | 0 |
| `manufacturing_new_orders_index.DE` | production and orders | M | index, 2021 = 100 | none | none | 0 | 0 |
| `manufacturing_production_index.DE` | production and orders | M | index, 2021 = 100 | none | none | 0 | 0 |
| `retail_sales_volume_index.DE` | production and orders | M | index, 2021 = 100 | none | none | 0 | 0 |
| `retail_sales_volume_index.EA` | production and orders | M | index, 2021 = 100 | none | none | 0 | 0 |
| `government_balance_ratio.DE` | public finances | Q | percent of GDP | none | none | 0 | 0 |
| `government_balance_ratio.EA` | public finances | Q | percent of GDP | none | none | 0 | 0 |
| `government_debt_ratio.DE` | public finances | Q | percent of GDP | none | none | 0 | 0 |
| `government_debt_ratio.EA` | public finances | Q | percent of GDP | none | none | 0 | 0 |
| `government_debt_ratio.FR` | public finances | Q | percent of GDP | none | none | 0 | 0 |
| `government_debt_ratio.IT` | public finances | Q | percent of GDP | none | none | 0 | 0 |
| `construction_confidence.DE` | sentiment and surveys | M | balance of positive and negative answers | none | none | 0 | 0 |
| `consumer_confidence.DE` | sentiment and surveys | M | balance of positive and negative answers | none | none | 0 | 0 |
| `consumer_confidence.EA` | sentiment and surveys | M | balance of positive and negative answers | none | none | 0 | 0 |
| `consumer_price_expectations.DE` | sentiment and surveys | M | balance of positive and negative answers | none | none | 0 | 0 |
| `consumer_price_expectations.EA` | sentiment and surveys | M | balance of positive and negative answers | none | none | 0 | 0 |
| `consumer_unemployment_expectations.DE` | sentiment and surveys | M | balance of positive and negative answers | none | none | 0 | 0 |
| `economic_sentiment_indicator.DE` | sentiment and surveys | M | index, long-term average = 100 | none | none | 0 | 0 |
| `economic_sentiment_indicator.EA` | sentiment and surveys | M | index, long-term average = 100 | none | none | 0 | 0 |
| `economic_sentiment_indicator.FR` | sentiment and surveys | M | index, long-term average = 100 | none | none | 0 | 0 |
| `economic_sentiment_indicator.IT` | sentiment and surveys | M | index, long-term average = 100 | none | none | 0 | 0 |
| `industry_confidence.DE` | sentiment and surveys | M | balance of positive and negative answers | none | none | 0 | 0 |
| `industry_confidence.EA` | sentiment and surveys | M | balance of positive and negative answers | none | none | 0 | 0 |
| `industry_employment_expectations.DE` | sentiment and surveys | M | balance of positive and negative answers | none | none | 0 | 0 |
| `industry_production_expectations.DE` | sentiment and surveys | M | balance of positive and negative answers | none | none | 0 | 0 |
| `industry_selling_price_expectations.DE` | sentiment and surveys | M | balance of positive and negative answers | none | none | 0 | 0 |
| `industry_selling_price_expectations.EA` | sentiment and surveys | M | balance of positive and negative answers | none | none | 0 | 0 |
| `retail_confidence.DE` | sentiment and surveys | M | balance of positive and negative answers | none | none | 0 | 0 |
| `services_confidence.DE` | sentiment and surveys | M | balance of positive and negative answers | none | none | 0 | 0 |
| `services_confidence.EA` | sentiment and surveys | M | balance of positive and negative answers | none | none | 0 | 0 |
| `construction_limited_by_labour.DE` | shortages | M | percent of firms | none | none | 0 | 0 |
| `construction_limited_by_material.DE` | shortages | M | percent of firms | none | none | 0 | 0 |
| `industry_limited_by_demand.DE` | shortages | Q | percent of firms | none | none | 0 | 0 |
| `industry_limited_by_financial_constraints.DE` | shortages | Q | percent of firms | none | none | 0 | 0 |
| `industry_limited_by_labour.DE` | shortages | Q | percent of firms | none | none | 0 | 0 |
| `industry_limited_by_labour.EA` | shortages | Q | percent of firms | none | none | 0 | 0 |
| `industry_limited_by_material_equipment.DE` | shortages | Q | percent of firms | none | none | 0 | 0 |
| `industry_limited_by_material_equipment.EA` | shortages | Q | percent of firms | none | none | 0 | 0 |
| `industry_not_limited.DE` | shortages | Q | percent of firms | none | none | 0 | 0 |
| `services_limited_by_labour.DE` | shortages | Q | percent of firms | none | none | 0 | 0 |
| `services_limited_by_space_equipment.DE` | shortages | Q | percent of firms | none | none | 0 | 0 |
| `goods_exports_value.DE` | trade | M | million euro | none | none | 0 | 0 |
| `goods_imports_value.DE` | trade | M | million euro | none | none | 0 | 0 |
| `goods_trade_balance.DE` | trade | M | million euro | none | none | 0 | 0 |
| `labour_cost_index_yoy.DE` | wages and labour costs | Q | percent change on the same quarter of the previous year | none | none | 0 | 0 |
| `labour_cost_index_yoy.EA` | wages and labour costs | Q | percent change on the same quarter of the previous year | none | none | 0 | 0 |
| `negotiated_wages_index.DE` | wages and labour costs | M | index, 2020 = 100 | none | none | 0 | 0 |

</details>

| Topic | Series |
|---|---|
| business demography | 2 |
| commodities | 35 |
| energy | 14 |
| exchange rates | 5 |
| financial stress | 2 |
| high frequency activity | 2 |
| housing | 3 |
| interest rates | 22 |
| labour market | 19 |
| money and credit | 3 |
| output and demand | 24 |
| prices | 46 |
| production and orders | 19 |
| public finances | 6 |
| sentiment and surveys | 19 |
| shortages | 11 |
| trade | 3 |
| wages and labour costs | 3 |

**Companies**

- **Registered companies:** 110 (90 listed, 82 with headquarters in Germany)

**Sources**

- **News outlets:** 50 configured (50 active)
- **Press-release sources:** 18 configured (18 active)

<details>
<summary>News outlets: items per source</summary>

| Source | Type | Status | Items | Last 30 days | Annotated | With lead text | Latest publication |
|---|---|---|---|---|---|---|---|
| agrarzeitung | trade press | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| airliners.de | trade press | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Augsburger Allgemeine | regional daily | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Automobilwoche | trade press | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Berliner Zeitung | regional daily | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Bild | tabloid | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| BR24 | public broadcaster regional | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Börsen-Zeitung | business daily | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Capital | business magazine | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| CHEManager | trade press | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Der Spiegel | weekly magazine | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Der Tagesspiegel | national daily | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Deutsche Handwerks Zeitung | trade press | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Deutschlandfunk | public broadcaster national | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Die Welt | national daily | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| DWDL.de | trade press | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| ES&T | trade press | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| FinanzNachrichten.de | financial portal | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Focus Online | weekly magazine | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Freie Presse | regional daily | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Hamburger Abendblatt | regional daily | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Handelsblatt | business daily | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| hessenschau.de | public broadcaster regional | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Immobilien Zeitung | trade press | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Kölner Stadt-Anzeiger | regional daily | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| manager magazin | business magazine | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| MDR | public broadcaster regional | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| n-tv.de | online only | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Neue Osnabrücker Zeitung | regional daily | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| onvista | financial portal | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| pv magazine Deutschland | trade press | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| rbb24 | public broadcaster regional | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Rheinische Post | regional daily | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Stern | weekly magazine | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Stuttgarter Zeitung | regional daily | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Süddeutsche Zeitung | national daily | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| t-online | online only | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| t3n | trade press | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| tagesschau.de | public broadcaster national | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| taz | national daily | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| teltarif.de | trade press | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Thüringer Allgemeine | regional daily | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| VDI nachrichten | trade press | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Versicherungswirtschaft heute | trade press | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| wallstreet-online | financial portal | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| WAZ | regional daily | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| WDR | public broadcaster regional | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Weser-Kurier | regional daily | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| WirtschaftsWoche | business magazine | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| ZDFheute | public broadcaster national | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |

</details>

<details>
<summary>Press-release sources: items per source</summary>

| Source | Type | Status | Items | Last 30 days | Annotated | With lead text | Latest publication |
|---|---|---|---|---|---|---|---|
| BMW Group | company | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Bundesanstalt für Finanzdienstleistungsaufsicht | public agency | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Continental | company | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Deutsche Bundesbank | central bank | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Deutsche Telekom | company | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Deutscher Gewerkschaftsbund | trade union | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Europäische Zentralbank | central bank | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Gesamtverband der Deutschen Versicherungswirtschaft | business association | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Handelsverband Deutschland | business association | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Henkel | company | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| ifo Institut | research institute | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Institut der deutschen Wirtschaft | research institute | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Institut für Arbeitsmarkt- und Berufsforschung | research institute | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Lufthansa Group | company | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| RWI - Leibniz-Institut für Wirtschaftsforschung | research institute | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Sachverständigenrat zur Begutachtung der gesamtwirtschaftlichen Entwicklung | research institute | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| thyssenkrupp | company | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |
| Volkswagen Group | company | active | 0 | 0 | 0.0% (0) | 0.0% (0) | none |

</details>

**Annotations**

- No news articles or press releases yet.
<!-- DATASET_OVERVIEW_END -->

## Datasets

| Dataset | Content | Source | Kind |
|---|---|---|---|
| `economic_series` | 238 statistical series: GDP and its components, production and new orders, truck toll mileage and the weekly activity index, HICP and national CPI, producer and import prices, energy prices, wages, labour market, interest rates and yields, money and credit, exchange rates, financial stress, trade, business and consumer surveys, shortages, public finances, house prices, insolvencies, commodity prices and electricity market data | Eurostat, ECB, Bundesbank, World Bank Pink Sheet, SMARD | vintage |
| `series_catalog` | The catalog of the series with concept, unit, frequency, provider and key, recorded when an entry appears or changes | `config/series.toml` | change |
| `companies` | The registry of 110 companies (DAX members, further large German companies, foreign companies) with sector, ISIN and Wikidata id, recorded when an entry appears or changes | `config/companies.toml` | change |
| `wikipedia_pageviews` | Daily views of the German Wikipedia articles of the registered companies, since July 2015 | Wikimedia | day series |
| `news_items` | Metadata of economic news articles of German outlets, business media, financial portals and trade publications | RSS feeds, news sitemaps, article pages | event |
| `press_releases` | Metadata of press releases of central banks, financial supervision, research institutes, associations, unions and companies | RSS feeds | event |
| `text_annotations` | Gemini labels of up to 400 news articles and press releases per run (press releases first): topic, sectors, companies with role and tone, institutions, countries, events, reported indicators and commodity prices with their direction, shortages, tone, economic outlook, uncertainty and recession mentions, frame | Gemini | event |

**Fields of every record:** `record_id`, `revision`, `dataset`, `schema_version`, `observed_at`, `source_id`, `source_url`, `license`, `backfilled`. All other fields are defined with descriptions in [src/schema.py](src/schema.py); the variables, the sector classification and the prediction targets they serve are described in [project_architecture.md](project_architecture.md).

**Point-in-time correctness.** `observed_at` is the time at which the pipeline observed the item. Filtering `observed_at <= t` gives the state of knowledge at time t, so that models can be tested on past data without information from the future. Records of items that are older than the start of collection (e.g. the history of a series at its first observation) have `backfilled: true`.

**No full texts.** News articles and press releases are stored as titles, URLs, metadata and derived variables. The lead text that Gemini reads is not stored.

**Annotated sample.** Every new economic item of a run is stored in `news_items` or `press_releases`. Up to 400 of them are annotated: all press releases, then news items in turns across the outlets, newest first. The other items are stored from the feed data without labels, so that the item counts per outlet stay complete and the annotated sample can be weighted against them.

### Statistical Series and Vintages

Statistical offices revise published values, and models trained on revised data overestimate what was knowable at the time. `economic_series` therefore stores vintages:

- **Revision 0** of a series holds all periods that the provider published at the first observation.
- **Every later revision** holds only the periods that were added or whose value changed, and lists the periods whose value disappeared in `removed_periods`. A run in which nothing changed writes no record.
- `first_period`, `last_period` and `observations` describe the complete series after the revision.

The series as it was known at time t is the result of applying the revisions observed at or before t in the order of `revision`:

```python
import duckdb

revisions = duckdb.sql("""
    select revision, observed_at, "values", removed_periods
    from read_json('data/economic_series/**/*.json', hive_partitioning=true)
    where series_id = 'gdp_real_qoq.DE' and observed_at <= '2027-03-01'
    order by revision
""").fetchall()
vintage = {}
for _, _, values, removed in revisions:
    vintage.update(values)
    for period in removed:
        vintage.pop(period, None)
```

Series ids have the form `<concept>.<geo>`, e.g. `hicp_inflation_yoy.DE` or `hicp_inflation_yoy.EA`. `geo` uses Eurostat country codes, `EA` for the euro area, `EU27_2020`, and `WLD` for world commodity prices. The catalog, the units and the provider keys of all series are in [config/series.toml](config/series.toml) and in the dataset `series_catalog`.

### News Items and Press Releases

| | `news_items` | `press_releases` |
|---|---|---|
| **Author** | A journalistic outlet (`outlet_id`) | An institution, association, union or company (`press_source_id`) |
| **Perspective** | Report about the economy by a third party | Self-presentation of the actor |
| **Sources** | Public broadcasters, national and regional newspapers, magazines, business dailies and magazines, financial portals, trade publications | Bundesbank, ECB, BaFin, German Council of Economic Experts, research institutes, associations, the DGB, corporate newsrooms |
| **Fields that describe the author** | `outlet_type`, `owner_group`, `home_state`, `outlet_sector` | `actor_type`, `company_id`, `jurisdiction` |
| **Stored** | Economic items only: from an economics feed or section, or with an economic term in title, teaser or keywords; all items of business media and trade publications | Every release |
| **Annotation order** | After the press releases, in turns across the outlets | First |
| **Annotation fields used** | All except `communication_type` (`Not applicable`) | All, including `communication_type` (purpose of the release) |

Both are labelled in `text_annotations`; the field `item_dataset` tells which of the two an annotation belongs to. Do not pool the two in an analysis without this distinction, e.g. when counting how often a company is mentioned or with which tone.

**Companies in the annotations.** Gemini names the companies of a text; the pipeline resolves the names against [config/companies.toml](config/companies.toml) (name and aliases, with or without legal form). Resolved companies are stored by id in `mentioned_companies` with their role and tone; other company names are stored as written in `other_companies`. The monthly source review lists frequent names that are not in the registry.

## Correlation with Other Datasets

The dataset is built to be correlated with [dataset.politics.germany](https://github.com/kleinnconrad/dataset.politics.germany), [dataset.technology](https://github.com/kleinnconrad/dataset.technology) and later datasets:

- **Time:** all records have `observed_at` and their own dates (periods, `published_at`, `daily_views`); aggregate all datasets to days, ISO weeks or months.
- **Articles:** the `record_id` of a news item is built from the normalized URL in the same way as in dataset.politics.germany, so an article that both pipelines collected has the same `record_id` in both datasets, with its political and its economic labels.
- **Outlets:** outlets that both datasets collect have the same id (e.g. `tagesschau`, `handelsblatt`, `welt`).
- **Entities:** companies, technologies and politicians carry Wikidata ids; countries and states use ISO 3166 codes; sectors map to NACE Rev. 2.

Examples and further keys are described in [project_architecture.md](project_architecture.md#4-correlation-with-other-datasets).

## Data Model

The diagram shows the seven datasets with all their fields, the two reference lists of the sources, and the fields that link them. Each field has a short comment; the full descriptions are in [src/schema.py](src/schema.py).

- **`common_fields`** lists the nine fields that every record of every dataset has. They are not repeated in the dataset entities.
- **`outlet` and `press_source`** are reference lists, not datasets: the outlets and press-release sources in [config/sources.toml](config/sources.toml), with the dates `added` and `removed` of their coverage period.
- **Types:** `list` and `map` are JSON arrays and objects; the comment names their content.

```mermaid
erDiagram
    common_fields {
        string record_id "stable id of the item, e.g. series:hicp_inflation_yoy.DE"
        int revision "0 for the first version, +1 per change"
        string dataset "name of the dataset"
        string schema_version "version of the record schema"
        datetime observed_at "UTC time the pipeline saw this version"
        string source_id "id of the API, file, outlet or press source"
        string source_url "URL of the item or API resource"
        string license "license or terms of the source"
        bool backfilled "older than the start of collection"
    }
    series_catalog {
        string series_id PK "concept.geo, e.g. hicp_inflation_yoy.DE"
        string concept "what the series measures"
        string name "name of the series"
        string topic "topic group, e.g. prices"
        string geo "country or area, e.g. DE, EA, WLD"
        string frequency "D, W, M, Q, S or A"
        string unit "unit of the values"
        string provider "eurostat, ecb, bundesbank, worldbank_cmo, smard"
        string provider_flow "dataset or dataflow of the provider"
        string provider_key "series key at the provider"
        date added "start of collection"
        date removed "end of collection"
        string removed_reason "why the series was removed"
    }
    economic_series {
        string series_id FK "series of the catalog"
        string concept "what the series measures"
        string topic "topic group"
        string geo "country or area"
        string frequency "D, W, M, Q, S or A"
        string unit "unit of the values"
        string provider "organization and interface"
        string provider_flow "dataset or dataflow"
        string provider_key "series key at the provider"
        string provider_title "title at the provider"
        string original_source "original compiler of redistributed data"
        map values "period to value: all at revision 0, changes later"
        list removed_periods "periods that disappeared"
        string first_period "first period of the complete series"
        string last_period "last period of the complete series"
        int observations "periods of the complete series"
        datetime source_updated "last update at the provider"
    }
    companies {
        string company_id PK "registry id, e.g. commerzbank"
        string name "name of the company or group"
        list aliases "further names for the resolution"
        string sector "main sector"
        string country "country of the headquarters"
        bool listed "shares listed on an exchange"
        string isin "ISIN of the main share line"
        string wikidata_qid "Wikidata id"
        date added "start of coverage"
        date removed "end of coverage"
        string removed_reason "why the company was removed"
    }
    wikipedia_pageviews {
        string company_id FK "company of the registry"
        string wikipedia_project "de.wikipedia"
        string wikipedia_title "article title at the request"
        string wikidata_qid "Wikidata id of the company"
        map daily_views "day to views by people"
    }
    outlet {
        string id PK "outlet id, e.g. handelsblatt"
        string name "display name"
        string outlet_type "e.g. business_daily, trade_press"
        string owner_group "publisher group, or public"
        string home_state "state of a regional outlet"
        string sector "sector of a trade publication"
        string paywall_model "free, mixed or hard"
        bool fetch_pages "article pages are fetched"
        date added "start of coverage"
        date removed "end of coverage"
    }
    press_source {
        string id PK "press source id, e.g. bundesbank"
        string name "issuing institution or company"
        string actor_type "e.g. central_bank, company"
        string company_id FK "registry id of a company"
        string jurisdiction "DE, state code, EU or INT"
        date added "start of coverage"
        date removed "end of coverage"
    }
    news_items {
        string outlet_id FK "outlet"
        string outlet_type "type of the outlet"
        string owner_group "publisher group"
        string home_state "state of a regional outlet"
        string outlet_sector "sector of a trade publication"
        string channel "rss or news_sitemap"
        string url "URL of the article"
        string canonical_url "canonical URL of the page"
        string title "title"
        datetime published_at "publication time"
        datetime updated_at "last modification time"
        string section "section of the outlet"
        list feed_categories "categories in the feed"
        list keywords "keywords of the page or sitemap"
        string jsonld_type "schema.org type of the page"
        bool is_agency_copy "credited to a news agency"
        int author_count "number of named authors"
        int word_count "word count of the page"
        bool is_paywalled "not accessible for free"
        bool has_video "page embeds a video"
        string content_basis "title_only, title_teaser or lead_text"
    }
    press_releases {
        string press_source_id FK "press source"
        string actor_type "type of the issuer"
        string company_id FK "issuing company"
        string jurisdiction "DE, state code, EU or INT"
        string url "URL of the release"
        string canonical_url "canonical URL of the page"
        string title "title"
        datetime published_at "publication time"
        list feed_categories "categories in the feed"
        string content_basis "title_only, title_teaser or lead_text"
    }
    text_annotations {
        string item_dataset "news_items or press_releases"
        string item_id FK "record_id of the item"
        string model "Gemini model"
        string extraction_hash "hash of prompt, schema and settings"
        string content_basis "text the model saw"
        bool is_economic "item is about the economy"
        string topic "main economic topic"
        list topics_secondary "up to two further topics"
        string issue_detail "specific issue in a few words"
        string article_type "news, opinion, interview, ..."
        list sectors "sectors the item is about"
        list mentioned_companies "registry ids of named companies"
        map company_roles "company id to subject, affected, commentator"
        map company_tone "company id to tone"
        list other_companies "names not in the registry"
        list institutions "institutions that act or comment"
        list countries "ISO 3166-1 alpha-2 codes"
        list states_concerned "German states"
        list event_types "economic events reported"
        string event_status "announced, ongoing or concluded"
        map indicators "indicator to reported direction"
        map commodities "commodity to price direction"
        list shortages "shortages reported"
        string overall_tone "positive, neutral, negative, mixed"
        string economic_outlook "improving, stable, deteriorating, ..."
        bool mentions_uncertainty "economic uncertainty mentioned"
        bool mentions_recession "recession mentioned"
        string policy_level "level of economic policy"
        bool government_involved "a government acts or is addressed"
        string frame "dominant news frame"
        list upcoming_events "future events with type and date"
        string communication_type "purpose of a press release"
    }
    series_catalog ||--o{ economic_series : "series_id"
    companies ||--o{ wikipedia_pageviews : "company_id"
    companies ||--o{ press_source : "company_id"
    outlet ||--o{ news_items : "outlet_id"
    press_source ||--o{ press_releases : "press_source_id"
    news_items ||--o| text_annotations : "item_id"
    press_releases ||--o| text_annotations : "item_id"
    companies }o--o{ text_annotations : "mentioned_companies"
```

## Example Records

One record per dataset, taken from test runs of the pipeline on 2026-10-25. The examples are linked:
- **News and annotation:** the Börsen-Zeitung article (`news_items`) has its Gemini labels in `text_annotations` (`item_id`).
- **Company:** the labels name company `commerzbank`. It appears in `companies` and in `wikipedia_pageviews` (`company_id`).
- **Series:** the series `hicp_inflation_yoy.DE` appears in `series_catalog` and in `economic_series` (`series_id`).

The values are unchanged from the data files, where each record is one line; here they are formatted for reading. Only `values` of the series example and `daily_views` of the pageviews example are shortened to the last three periods.

<details>
<summary><code>economic_series</code>: the annual HICP inflation rate of Germany at its first observation (values shortened)</summary>

```json
{
  "record_id": "series:hicp_inflation_yoy.DE",
  "revision": 0,
  "dataset": "economic_series",
  "schema_version": "1.0",
  "observed_at": "2026-10-25T14:01:25Z",
  "source_id": "eurostat",
  "source_url": "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/prc_hicp_minr/M.RCH_A.TOTAL.DE",
  "license": "Eurostat (reuse authorised with acknowledgement of the source)",
  "backfilled": true,
  "series_id": "hicp_inflation_yoy.DE",
  "concept": "hicp_inflation_yoy",
  "topic": "prices",
  "geo": "DE",
  "frequency": "M",
  "unit": "percent change on the same month of the previous year",
  "provider": "eurostat",
  "provider_flow": "prc_hicp_minr",
  "provider_key": "M.RCH_A.TOTAL.DE",
  "provider_title": null,
  "original_source": null,
  "values": {
    "2026-07": 2.8,
    "2026-08": 2.9,
    "2026-09": 3.3
  },
  "removed_periods": [],
  "first_period": "1997-01",
  "last_period": "2026-09",
  "observations": 357,
  "source_updated": "2026-10-16T23:00:00Z"
}
```

</details>

<details>
<summary><code>series_catalog</code>: the catalog entry of the same series</summary>

```json
{
  "record_id": "series_catalog:hicp_inflation_yoy.DE",
  "revision": 0,
  "dataset": "series_catalog",
  "schema_version": "1.0",
  "observed_at": "2026-10-25T15:19:39Z",
  "source_id": "registry",
  "source_url": "https://github.com/kleinnconrad/dataset.economics.germany/blob/main/config/series.toml",
  "license": "Configuration of this project; no license granted",
  "backfilled": false,
  "series_id": "hicp_inflation_yoy.DE",
  "concept": "hicp_inflation_yoy",
  "name": "Harmonised index of consumer prices (ECOICOP ver. 2), all items, annual rate of change",
  "topic": "prices",
  "geo": "DE",
  "frequency": "M",
  "unit": "percent change on the same month of the previous year",
  "provider": "eurostat",
  "provider_flow": "prc_hicp_minr",
  "provider_key": "M.RCH_A.TOTAL.DE",
  "added": "2026-10-25",
  "removed": null,
  "removed_reason": null
}
```

</details>

<details>
<summary><code>companies</code>: Commerzbank in the company registry</summary>

```json
{
  "record_id": "companies:commerzbank",
  "revision": 0,
  "dataset": "companies",
  "schema_version": "1.0",
  "observed_at": "2026-10-25T15:19:39Z",
  "source_id": "registry",
  "source_url": "https://github.com/kleinnconrad/dataset.economics.germany/blob/main/config/companies.toml",
  "license": "Configuration of this project; no license granted",
  "backfilled": false,
  "company_id": "commerzbank",
  "name": "Commerzbank",
  "aliases": [],
  "sector": "Banking and financial services",
  "country": "DE",
  "listed": true,
  "isin": "DE000CBK1001",
  "wikidata_qid": "Q157617",
  "added": "2026-10-25",
  "removed": null,
  "removed_reason": null
}
```

</details>

<details>
<summary><code>wikipedia_pageviews</code>: the daily views of the Commerzbank article (shortened)</summary>

```json
{
  "record_id": "pageviews:commerzbank:2015-07-01:2026-10-24",
  "revision": 0,
  "dataset": "wikipedia_pageviews",
  "schema_version": "1.0",
  "observed_at": "2026-10-25T14:06:55Z",
  "source_id": "wikimedia_pageviews",
  "source_url": "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/de.wikipedia.org/all-access/user/Commerzbank/daily/20150701/20261024",
  "license": "CC0-1.0",
  "backfilled": true,
  "company_id": "commerzbank",
  "wikipedia_project": "de.wikipedia",
  "wikipedia_title": "Commerzbank",
  "wikidata_qid": "Q157617",
  "daily_views": {
    "2026-10-22": 441,
    "2026-10-23": 346,
    "2026-10-24": 246
  }
}
```

</details>

<details>
<summary><code>news_items</code>: a Börsen-Zeitung article on the pressure on France</summary>

```json
{
  "record_id": "news:fffa8de0f12fbe3b",
  "revision": 0,
  "dataset": "news_items",
  "schema_version": "1.0",
  "observed_at": "2026-10-25T15:18:18Z",
  "source_id": "boersen_zeitung",
  "source_url": "https://www.boersen-zeitung.de/news/bz-all-rss/konjunktur-politik/frankreich-von-allen-seiten-unter-druck",
  "license": "Publisher rights; metadata only",
  "backfilled": false,
  "outlet_id": "boersen_zeitung",
  "outlet_type": "business_daily",
  "owner_group": "WM Gruppe",
  "home_state": null,
  "outlet_sector": null,
  "channel": "rss",
  "url": "https://www.boersen-zeitung.de/news/bz-all-rss/konjunktur-politik/frankreich-von-allen-seiten-unter-druck",
  "canonical_url": "https://www.boersen-zeitung.de/konjunktur-politik/frankreich-von-allen-seiten-unter-druck",
  "title": "Frankreich von allen Seiten unter Druck",
  "published_at": "2026-10-25T14:50:56Z",
  "updated_at": "2026-10-25T14:50:57Z",
  "section": "konjunktur-politik",
  "feed_categories": [
    "konjunktur-politik"
  ],
  "keywords": [],
  "jsonld_type": "NewsArticle",
  "is_agency_copy": false,
  "author_count": 3,
  "word_count": null,
  "is_paywalled": true,
  "has_video": false,
  "content_basis": "lead_text"
}
```

</details>

<details>
<summary><code>press_releases</code>: a press release of the Volkswagen Group</summary>

```json
{
  "record_id": "press:f19a9e83e1f219c2",
  "revision": 0,
  "dataset": "press_releases",
  "schema_version": "1.0",
  "observed_at": "2026-10-25T15:05:35Z",
  "source_id": "volkswagen_press",
  "source_url": "https://www.volkswagen-group.com/de/pressemitteilungen/zweites-ueberpruefungsgespraech-volkswagen-ag-und-ig-metall-einigen-sich-auf-den-start-von-verhandlungen-20757",
  "license": "Publisher rights; metadata only",
  "backfilled": false,
  "press_source_id": "volkswagen_press",
  "actor_type": "company",
  "company_id": "volkswagen",
  "jurisdiction": "DE",
  "url": "https://www.volkswagen-group.com/de/pressemitteilungen/zweites-ueberpruefungsgespraech-volkswagen-ag-und-ig-metall-einigen-sich-auf-den-start-von-verhandlungen-20757",
  "canonical_url": "https://www.volkswagen-group.com/de/pressemitteilungen/zweites-ueberpruefungsgespraech-volkswagen-ag-und-ig-metall-einigen-sich-auf-den-start-von-verhandlungen-20757",
  "title": "Zweites Überprüfungsgespräch: Volkswagen AG und IG Metall einigen sich auf den Start von Verhandlungen",
  "published_at": "2026-10-23T00:00:00Z",
  "feed_categories": [],
  "content_basis": "lead_text"
}
```

</details>

<details>
<summary><code>text_annotations</code>: the Gemini labels of the Börsen-Zeitung article</summary>

```json
{
  "record_id": "annotation:news:fffa8de0f12fbe3b:5bb86726b9727d69",
  "revision": 0,
  "dataset": "text_annotations",
  "schema_version": "1.0",
  "observed_at": "2026-10-25T15:18:44Z",
  "source_id": "boersen_zeitung",
  "source_url": "https://www.boersen-zeitung.de/news/bz-all-rss/konjunktur-politik/frankreich-von-allen-seiten-unter-druck",
  "license": "Derived data of this project; no license granted",
  "backfilled": false,
  "item_dataset": "news_items",
  "item_id": "news:fffa8de0f12fbe3b",
  "model": "gemini-2.5-flash",
  "extraction_hash": "5bb86726b9727d69",
  "content_basis": "lead_text",
  "is_economic": true,
  "topic": "Public finances and taxes",
  "topics_secondary": [
    "Monetary policy and interest rates",
    "Growth and business cycle"
  ],
  "issue_detail": "Frankreich unter Druck",
  "article_type": "News",
  "sectors": [],
  "mentioned_companies": [
    "commerzbank"
  ],
  "company_roles": {
    "commerzbank": "Commentator"
  },
  "company_tone": {
    "commerzbank": "Neutral"
  },
  "other_companies": [],
  "institutions": [
    "European Central Bank",
    "Other"
  ],
  "countries": [
    "FR"
  ],
  "states_concerned": [],
  "event_types": [
    "Budget decision"
  ],
  "event_status": "Ongoing",
  "indicators": {
    "Interest rates": "Rising"
  },
  "commodities": {},
  "shortages": [],
  "overall_tone": "Negative",
  "economic_outlook": "Deteriorating",
  "mentions_uncertainty": false,
  "mentions_recession": false,
  "policy_level": "European Union",
  "government_involved": true,
  "frame": "Economic consequences",
  "upcoming_events": [],
  "communication_type": "Not applicable"
}
```

</details>

## Sources and Fetch Rules

- **APIs and data files:** Eurostat, ECB and Bundesbank (SDMX 2.1 REST, SDMX-CSV), the World Bank Pink Sheet (xlsx), SMARD (JSON), the Wikimedia Pageviews API and the Wikidata API. These documented interfaces are used under their terms, without keys.
- **Websites:** the news outlets and press-release sources in [config/sources.toml](config/sources.toml), read through RSS/Atom feeds, news sitemaps and, where permitted, the article pages; the commodity markets page of the World Bank, which links the current Pink Sheet.
- **robots.txt:** every website request is checked against the robots.txt of its host for the user agent `GermanEconomicsDataset`, with the longest-match rule of RFC 9309. A crawl delay is honored; a host that requires more than 120 seconds is not fetched.
- **Bot protection:** a source that answers with HTTP 401/403, a challenge page or a CAPTCHA is set to `blocked` and is not fetched again until it is reset by hand. The pipeline does not use a headless browser.
- **Text and data mining reservations:** a source whose host or pages declare a machine-readable reservation (TDMRep header, `/.well-known/tdmrep.json` or meta tag) is set to `tdm_reserved` and is not used. For outlets whose robots.txt states a reservation under § 44b UrhG in plain text, article pages are not fetched (`fetch_pages = false`); their feed items are used with title and teaser only.
- **Pacing:** at most one request per second per host, retries for server errors and rate limits.
- **Source review:** on the first day of every month, `source_review.yml` checks the list and proposes removals, fixes and additions as a pull request (see [Workflows](#workflows)).

## Pipeline

```mermaid
sequenceDiagram
    participant Action as GitHub Actions
    participant Run as main.py / pipeline.py
    participant Web as Feeds and pages
    participant Gemini as Gemini API
    participant Stats as Eurostat / ECB / Bundesbank
    participant Files as Pink Sheet / SMARD
    participant Wiki as Wikimedia / Wikidata
    participant Store as storage.py / state.py

    Action->>Run: Pipeline run (Tuesdays and Fridays, 02:07 Europe/Berlin)
    Run->>Store: New and changed entries of the series catalog and the company registry
    Run->>Web: Feeds and news sitemaps of all due sources
    loop Up to 400 new items (press releases first), in turns across the sources
        Run->>Web: Article page (metadata, lead text), where permitted
        Run->>Gemini: Batches of 10 items, up to 4 at the same time
        Gemini-->>Run: Labels per item, company names resolved against the registry
        Run->>Store: Items and annotations (every 100 items)
    end
    Run->>Store: Further new items without labels
    Run->>Stats: Every catalog series (SDMX-CSV)
    Run->>Store: New and revised vintages
    Run->>Files: SMARD daily data; Pink Sheet if it changed (once a week)
    Run->>Wiki: Daily views of the company articles since the last stored day (once a week)
    Action->>Action: Update the README overview, commit data/
```

The feeds run right after the registries, because news items leave the feeds after a few days; the statistical series can also be fetched by a later run, because their providers keep the history. `commodities` and `wikipedia_pageviews` run once a week, six days or more after their last complete run.

**Run deadline.** The collectors start no new work 25 minutes after the start of the run (`RUN_DEADLINE_MINUTES`), so that the workflow commits the data before its timeout of 30 minutes. A collector that stops at the deadline has the status `partial` and continues in the next run; a collector that has not started by then is skipped. Items of the feeds that are not annotated by the deadline are stored without labels.

Each collector runs in isolation: a failure is logged in `data/state/collectors.json` and the run log, the other collectors continue, and the data already written is kept. The run then ends with exit code 1, so that the workflow fails visibly.

## Data Files

| Path | Content |
|---|---|
| `data/<dataset>/year=YYYY/month=MM/<dataset>_YYYY-MM-DD.json` | Records of a dataset observed on one UTC day |
| `data/state/seen/<dataset>.json` | Items already written, with content hash and revision |
| `data/state/seen/economic_series/<series_id>.json` | Current values of a series, compared with the next download |
| `data/state/collectors.json` | First run, last run, failures and cursor per collector |
| `data/state/sources.json` | Health status of the news and press-release sources |
| `data/state/run_log.jsonl` | One line per run with the outcome and counters of each collector |

Each data file is a JSON list with one record per line. The folder names `year=` and `month=` let DuckDB, Polars and pyarrow read a dataset as one table:

```python
import duckdb
news = duckdb.sql("select * from read_json('data/news_items/**/*.json', hive_partitioning=true)").df()
```

## Workflows

| Workflow | Schedule | Purpose |
|---|---|---|
| `pipeline.yml` | Tuesdays and Fridays, 02:07 Europe/Berlin | Runs the due collectors (timeout 30 minutes), updates the overview and commits `data/` and `README.md` |
| `notify.yml` | After each `normal` or `backfill` run of `pipeline.yml` | Posts a summary of the run (status and records per collector, new and revised series, annotated items, Gemini tokens and estimated cost) as a commit comment that mentions the repository owner |
| `source_review.yml` | First day of every month, 07:17 Europe/Berlin | Checks the sources and proposes changes of `config/sources.toml` as a pull request; reports unregistered companies and stale series |
| `ci.yml` | Pull requests, pushes to `main` | Lint, tests and commit message checks |

**Notification email.** GitHub sends an email for the mention in the comment of `notify.yml` if email notifications for participating and @mentions are enabled (the default, under **Settings > Notifications** of the GitHub account). The summary is built by `scripts/run_summary.py` from the last line of `data/state/run_log.jsonl`; the cost estimate uses the list prices in that script.

**Source review.** `source_review.yml` (code in [src/source_review.py](src/source_review.py)) proposes changes of `config/sources.toml` as a pull request from the branch `source-review`; they take effect when the pull request is merged. The description lists every change with its reason.
- **Removals:** sources that are `blocked` or `tdm_reserved`, that are `broken` and still fail, that have no working feed left, whose robots.txt requires a crawl delay above 120 seconds, or that yielded no economic item in 90 days. A removed source keeps its entry with `removed` and `removed_reason`. To keep a source with low yield, set `keep = true` in its entry.
- **Fixes:** feeds that return HTTP 404 or 410, are disallowed by robots.txt or whose newest item is older than 180 days are removed; feeds that moved permanently get their new URL. Page fetching is turned off where robots.txt states a TDM reservation in natural language or requires a crawl delay above 10 seconds.
- **Additions:** Gemini with Google Search looks for the official press-release feeds of the federal economic institutions, of business associations, research institutes and trade unions, of the newsrooms of registered companies without a press source (the most frequently named first) and of trade publications for sectors without one. Each candidate is checked with the fetch rules of the pipeline: readable robots.txt, no TDM reservation, no bot protection, and recent items. At most five sources are added per review, with `added` set to the review date.
- **Exclusions:** rejected candidates are added to the `[[excluded]]` entries with their attributes, so that the search does not propose them again. Blocked, TDM-reserved, duplicate and irrelevant candidates stay excluded until the entry is changed by hand; every review checks the others again.
- **Registries:** the description lists company names of the annotations of the last 90 days that are not in `config/companies.toml`, and catalog series whose newest period is older than expected for their frequency. Add a company with its verified Wikidata id, or update a series in `config/series.toml` and record the change in the measurement log of [project_architecture.md](project_architecture.md#11-measurement-log).

The review sends about four Gemini requests with Google Search per month, which cost a few cents. A pull request opened with the `GITHUB_TOKEN` starts no workflows, so the review starts `ci.yml` on its branch. The next review rebuilds the branch, so merge or close the pull request before the first day of the next month.

**Manual runs.** The workflows can be started by hand: open the **Actions** tab, select **German Economics Pipeline** (or **Source Review**, **CI**), click **Run workflow**, and choose the branch and the inputs. The modes of `pipeline.yml`:
- `normal`: same as the scheduled run; commits the data.
- `backfill`: imports the history of all collectors except the feeds, without the weekly intervals, and commits it (timeout 90 minutes).
- `shadow`: runs on a copy of the state in a temporary folder and uploads the output as an artifact; nothing is committed.
- `dry-run`: runs the collectors without writing any data; the feeds collector reads the feeds and sitemaps only (no article pages, no Gemini calls).

The input `collectors` restricts a manual run to a comma-separated list of collectors, e.g. `feeds`; selected collectors run even if they are not due.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | none | Gemini API key (required for the annotation of news and press releases and for the search of the source review) |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Model for the annotation; stored in every annotation record |
| `MAX_GEMINI_CALLS_PER_RUN` | 50 | Gemini requests per run, including retries |
| `MAX_ANNOTATIONS_PER_RUN` | 400 | News articles and press releases annotated per run; further new items are stored without labels |
| `GEMINI_CONCURRENCY` | 4 | Gemini requests sent at the same time; 1 for the free tier of the Gemini API |
| `NEWS_LOOKBACK_HOURS` | 96 | Age limit of new feed and sitemap items |
| `NEWS_FETCH_PAGES` | on | Fetch article pages for metadata and lead text |
| `RUN_DEADLINE_MINUTES` | 25 | Minutes after the start after which the collectors start no new work (85 in `backfill` runs) |
| `COLLECTORS` | all due | Comma-separated list of collectors to run; listed collectors run even if they are not due |

The statistical series, companies and sources are configured in [config/series.toml](config/series.toml), [config/companies.toml](config/companies.toml) and [config/sources.toml](config/sources.toml). Fixed thresholds, such as the source status rules, are constants in the modules that use them.

## Running Locally

```bash
uv sync
uv run python src/main.py --dry-run --collectors feeds              # read the feeds only
uv run python src/main.py --collectors ecb,bundesbank,eurostat       # statistical series
uv run python src/main.py --backfill                                 # import the history (no feeds)
uv run python src/main.py --max-annotations 20                       # a short full run
uv run python src/generate_dataset_overview.py                       # README overview
uv run python src/source_review.py --report review.md --no-search    # source review; changes config/sources.toml
```

Secrets are read from a `.env` file in the repository root (`GEMINI_API_KEY=...`); the file is listed in `.gitignore`. Local runs write to `~/Downloads/german_economics_dataset/` unless `--output-dir` is given; in GitHub Actions they write to `data/`. The collectors, in the order of a run, are `series_catalog`, `companies`, `feeds`, `ecb`, `bundesbank`, `eurostat`, `electricity`, `commodities` and `wikipedia_pageviews`.

## Continuous Integration

The `CI` workflow runs on every pull request and on pushes to `main`:

| Job | Checks |
|---|---|
| `Lint` | `uv.lock` matches `pyproject.toml`; `ruff check`; `actionlint` (including `shellcheck`) on the workflow files |
| `Tests` | The tests in `tests/` on Python 3.11 and 3.14. They run offline, with a fake web and a fake Gemini client, and check that every module imports, that the configuration files are valid and that the README matches the schema. |
| `Conventional Commits` | Every commit of a pull request follows the Conventional Commits format (pull requests only) |
| `CI passed` | Succeeds only if all jobs above succeeded or were skipped; use it as the required status check of `main` |

Dependencies are managed with [uv](https://docs.astral.sh/uv/): `pyproject.toml` declares them, `uv.lock` pins them, and Dependabot proposes weekly updates. Run the checks locally before pushing:

```bash
uv lock --check
uv run ruff check .
uv run pytest
```

## Setup

1. Add the repository secret `GEMINI_API_KEY` under **Settings > Secrets and variables > Actions**.
2. Under **Settings > Actions > General > Workflow permissions**, choose read and write permissions, so that the workflows can push, and allow GitHub Actions to create and approve pull requests, so that the source review can open its pull request.
3. Start `pipeline.yml` once by hand in the mode `backfill`. It imports the history of all series (from 1949 for the national CPI, from 1960 for commodity prices, from 2015 for electricity data and pageviews) and takes about 10 minutes. Without the backfill, the first scheduled run imports the same history.

## Sources and Attribution

No license is granted for the code or the data of this repository. The data contains material of third parties, which remains subject to the terms of its sources; the field `license` of every record names them:

| Source | Datasets | Terms and required attribution |
|---|---|---|
| Eurostat (https://ec.europa.eu/eurostat) | `economic_series` | Reuse authorised with acknowledgement of the source: "Source: Eurostat". The business and consumer surveys are conducted by the European Commission (DG ECFIN). |
| European Central Bank, ECB Data Portal (https://data.ecb.europa.eu) | `economic_series` | Reuse free of charge with acknowledgement of the source: "Source: ECB". |
| Deutsche Bundesbank, time series database (https://www.bundesbank.de) | `economic_series` | Reuse with attribution: "Source: Deutsche Bundesbank"; redistributed series name their original compiler (Statistisches Bundesamt, Bundesagentur für Arbeit) in `original_source`. |
| World Bank Commodity Price Data, Pink Sheet (https://www.worldbank.org/en/research/commodity-markets) | `economic_series` | CC BY 4.0: "Source: World Bank". |
| Bundesnetzagentur, SMARD (https://www.smard.de) | `economic_series` | CC BY 4.0: "Bundesnetzagentur \| SMARD.de". |
| Wikimedia Foundation, Pageviews API; Wikidata | `wikipedia_pageviews`, Wikidata ids of `companies` | CC0 1.0 |
| News outlets and press-release issuers listed in `config/sources.toml` | `news_items`, `press_releases` | Rights of the publishers. Only titles, URLs, metadata and derived variables are stored; the texts are not stored. |

The labels in `text_annotations` were produced with Google Gemini by this project.
