# German Economics Dataset: Architecture

This document describes the structure of the pipeline: scope and decisions, the design rules for a long collection period, the datasets and their variables, how the dataset is correlated with other datasets, the prediction targets, the sources, storage and data volume, the run, failure handling, the measurement log and the implementation status. The pipeline adopts the structure of [dataset.politics.germany](https://github.com/kleinnconrad/dataset.politics.germany) and [dataset.technology](https://github.com/kleinnconrad/dataset.technology). Usage and configuration are described in the [README](README.md).

## Table of Contents
- [1. Scope and Decisions](#1-scope-and-decisions)
- [2. Design Rules](#2-design-rules)
- [3. Datasets and Variables](#3-datasets-and-variables)
  - [3.1 Common Fields](#31-common-fields)
  - [3.2 Statistical Series](#32-statistical-series)
  - [3.3 Companies and Attention](#33-companies-and-attention)
  - [3.4 News and Press Releases](#34-news-and-press-releases)
  - [3.5 Text Annotations](#35-text-annotations)
  - [3.6 Sectors](#36-sectors)
- [4. Correlation with Other Datasets](#4-correlation-with-other-datasets)
- [5. Prediction Targets](#5-prediction-targets)
- [6. Sources and Fetch Rules](#6-sources-and-fetch-rules)
- [7. Storage, Partitioning and Data Volume](#7-storage-partitioning-and-data-volume)
- [8. Repository Structure](#8-repository-structure)
- [9. Pipeline Run](#9-pipeline-run)
- [10. Failure Handling](#10-failure-handling)
- [11. Measurement Log](#11-measurement-log)
- [12. Implementation Status](#12-implementation-status)

---

## 1. Scope and Decisions

- **Scope:** the German economy. Statistical series cover Germany and, where they explain the German economy, the euro area (ECB policy, euro area aggregates), the main European trading partners (France, Italy, Spain, Netherlands, Poland, Austria for selected series) and world commodity prices. The press side covers German economic journalism, the communication of economic institutions and the newsrooms of large companies.
- **Horizon:** the data is collected over many years and analyzed as long time series. The design favors stable definitions, durable sources and a moderate data volume over the completeness of single items.
- **Repository:** public. No license is granted for the code or the data of this repository. Every record names the license or terms of its source in the field `license`; the sources and their attribution requirements are listed in the [README](README.md#sources-and-attribution).
- **Schedule:** one workflow runs the due collectors on Tuesdays and Fridays at 02:07 Europe/Berlin, the schedule of dataset.politics.germany. A run takes at most 30 minutes; the history is imported by the first run or by a separate `backfill` run.
- **Model:** Google Gemini (`gemini-2.5-flash` by default, thinking off) labels up to 400 news articles and press releases per run, with the request handling of dataset.politics.germany. At the measured token use of about 4,300 input and 3,100 output tokens per request of ten items, this costs about $0.36 per run.
- **No paid access:** every source is free and needs no key. The Gemini API key is the only secret.

**Consequence of the schedule for news.** RSS feeds and news sitemaps list only recent items; many feeds cover less than three days. With runs every three or four days and a lookback of 96 hours, the pipeline collects what the feeds still list at run time, so news coverage is a sample, not a complete record. The statistical series are not affected: their providers keep the history, and every run fetches the complete series.

---

## 2. Design Rules

1. **Point-in-time correctness.** Every record has `observed_at`, the UTC time at which the pipeline observed it. Filtering `observed_at <= t` reproduces what was known at time t. Records of items older than the start of collection have `backfilled: true`.
2. **Vintages of statistical series.** Statistical offices revise published values. `economic_series` stores the complete series at its first observation (revision 0) and afterwards, with the next revision, only the periods that were added, revised or removed. Replaying the revisions in the order of `observed_at` gives the real-time data set: the series as it was known on any day, without look-ahead bias.
3. **Five kinds of datasets.**
   - *Vintage:* `economic_series` (rule 2).
   - *Day series:* `wikipedia_pageviews` stores, per company and run, the days since the last stored day.
   - *Change:* `series_catalog` and `companies` store an entry when it appears and again when a field changes.
   - *Event:* `news_items`, `press_releases` and `text_annotations` store each item once.
4. **Raw data and annotations are separated.** Gemini labels are stored in `text_annotations`, keyed by item and `extraction_hash`, so that they can be regenerated with another model or prompt without changing the raw data.
5. **Declarative registries.** The statistical series (`config/series.toml`), the companies (`config/companies.toml`) and the news and press sources (`config/sources.toml`) are configuration files with `added` and `removed` dates. Their entries are written to datasets, so that the coverage of every series, company and source is known from the data alone.
6. **Permanent identifiers.** Series ids (`<concept>.<geo>`), company ids, source ids, dataset names, field names and `record_id` formats are never reused for a different meaning.
7. **Additive schema changes.** New fields get a description and are added without changing existing ones; a changed meaning requires a new field and a new `SCHEMA_VERSION`. A snapshot test guards the record schema.
8. **Raw values, derived variables later.** The datasets store values as the sources report them. Growth rates, spreads, moving averages and other features are computed in the analysis.
9. **No full texts, no private persons.** Only titles, URLs, metadata and derived variables of articles and press releases are stored. Companies and institutions are public actors and are stored by name; names of persons are not labelled.
10. **Logged measurement changes.** Every change of a source, key, filter, unit or counting rule is recorded in the measurement log (Section 11), so that structural breaks can be identified.

---

## 3. Datasets and Variables

All fields are defined with descriptions in [src/schema.py](src/schema.py); the README shows the data model and one example record per dataset.

### 3.1 Common Fields

Every record has: `record_id`, `revision`, `dataset`, `schema_version`, `observed_at`, `source_id`, `source_url`, `license`, `backfilled`.

### 3.2 Statistical Series

**`economic_series`** (vintage): series_id, concept, topic, geo, frequency, unit, provider, provider_flow, provider_key, provider_title, original_source, values {period: value}, removed_periods, first_period, last_period, observations, source_updated.

**`series_catalog`** (change): the entries of [config/series.toml](config/series.toml) with series_id, concept, name, topic, geo, frequency, unit, provider, provider_flow, provider_key, added, removed, removed_reason.

A catalog entry describes one concept (e.g. `hicp_inflation_yoy`) at one provider and expands to one series per geo with the id `<concept>.<geo>`. Geo codes follow Eurostat: country codes, `EA` for the euro area and `EU27_2020`; `WLD` for world prices. Periods are stored as `YYYY-MM-DD`, `YYYY-Www`, `YYYY-MM`, `YYYY-Qn`, `YYYY-Sn` or `YYYY`.

The initial catalog has 238 series:

| Topic | Series (concepts) | Providers |
|---|---|---|
| output_and_demand | real GDP growth (quarter on quarter and year on year, 8 countries and areas), real and nominal GDP levels, household and government consumption, fixed investment, exports and imports | Eurostat |
| production_and_orders | industrial production (Germany, euro area, France, Italy), manufacturing and the sectors automotive, chemicals, machinery and basic metals, construction, retail sales, manufacturing new orders (total, without large orders, domestic, foreign), capacity utilization | Eurostat, Bundesbank |
| high_frequency_activity | truck toll mileage index (daily), weekly activity index of the Bundesbank | Bundesbank |
| prices | HICP (all items, core, energy, food, services, non-energy goods; 8 countries and areas for the headline rate), national CPI, producer prices, import prices, electricity and gas prices for households and industry (half-yearly) | Eurostat, Bundesbank |
| wages_and_labour_costs | negotiated wages, labour cost index | Bundesbank, Eurostat |
| labour_market | unemployment rate (ILO, 8 countries and areas), youth unemployment, registered unemployment and vacancies, short-time workers, employment, job vacancy rate | Eurostat, Bundesbank |
| interest_rates | ECB key rates, euro short-term rate, Euribor, euro area AAA yield curve, yields of Federal securities (2, 5, 10, 30 years), long-term interest rates of five countries, expected real interest rate, mortgage and corporate loan rates | ECB, Bundesbank |
| money_and_credit | M3 growth, growth of loans to non-financial corporations | ECB |
| exchange_rates | euro reference rates against US dollar, yuan, pound, franc and yen | ECB |
| financial_stress | Composite Indicator of Systemic Stress (Germany, euro area) | ECB |
| trade | exports, imports and trade balance of goods | Eurostat |
| sentiment_and_surveys | economic sentiment indicator, confidence in industry, services, retail, construction and of consumers, production, selling price and employment expectations, consumer price and unemployment expectations | Eurostat (European Commission surveys) |
| shortages | shares of firms whose activity is limited by shortage of material and equipment, labour, demand or finance (industry, services, construction) | Eurostat (European Commission surveys) |
| public_finances | government debt ratio, government balance | Eurostat |
| housing | house price index and its annual rate | Eurostat |
| business_demography | bankruptcy declarations, business registrations | Eurostat |
| commodities | 26 monthly prices (Brent, natural gas Europe and US, coal, aluminium, copper, iron ore, nickel, zinc, lead, tin, gold, silver, platinum, wheat, maize, soybeans, palm oil, sugar, coffee, cocoa, cotton, urea, DAP, potassium chloride) and 9 price indices | World Bank Pink Sheet |
| energy | day-ahead electricity price, grid load, residual load, net generation by source (lignite, hard coal, gas, other conventional, wind onshore and offshore, solar, biomass, hydro, pumped storage, other renewables) | SMARD |

### 3.3 Companies and Attention

**`companies`** (change): the entries of [config/companies.toml](config/companies.toml): company_id, name, aliases, sector, country, listed, isin, wikidata_qid, added, removed, removed_reason. The initial registry has 110 companies: the 40 members of the DAX on 2026-10-25, 28 further listed German companies, 16 unlisted German companies and 26 foreign companies with a strong presence in German economic news. Index memberships are not stored, because they change.

**`wikipedia_pageviews`** (day series): daily views by people of the German Wikipedia article of every registered company, resolved from its Wikidata id. Pageviews measure public attention; they react to profit warnings, scandals, job cuts and product launches.

### 3.4 News and Press Releases

**Outlet attributes** (in `config/sources.toml`, copied into each record): `outlet_type`, `owner_group`, `home_state`, the sector of a trade publication (`outlet_sector`) and the paywall model.

**`news_items`:** outlet_id, outlet_type, owner_group, home_state, outlet_sector, channel (rss or news_sitemap), url, canonical_url, title, published_at, updated_at, section, feed_categories, keywords, jsonld_type, is_agency_copy, author_count, word_count, is_paywalled, has_video, content_basis (title_only, title_teaser, lead_text).

**`press_releases`:** press_source_id, actor_type (federal government, federal ministry, state government, central bank, statistical office, public agency, EU institution, international organization, research institute, business association, trade union, company), company_id of an issuing company, jurisdiction (DE, a state, EU or INT), url, canonical_url, title, published_at, feed_categories, content_basis.

News items of general outlets are stored only if they come from an economics feed or section, or contain an economic term in title, teaser or keywords (`ECONOMICS_TERMS` in [src/collectors/feeds.py](src/collectors/feeds.py)). Items of business dailies and magazines, financial portals and trade publications and all press releases are stored without this filter.

### 3.5 Text Annotations

`text_annotations` holds the Gemini labels of news articles and press releases.

| Group | Variables |
|---|---|
| Relevance and topic | is_economic, topic, topics_secondary, issue_detail |
| Form | article_type (news, opinion, interview, analysis, live blog, explainer, press release) |
| Actors | sectors, mentioned_companies (registry ids), company_roles {id: subject, affected, commentator}, company_tone, other_companies (names not in the registry), institutions |
| Geography | countries (ISO 3166-1 alpha-2), states_concerned |
| Events | event_types, event_status (announced or planned, ongoing, concluded), upcoming_events [{event_type, date}] |
| Indicators and markets | indicators {indicator: rising, falling, unchanged, not stated}, commodities {commodity: price direction}, shortages |
| Tone and expectations | overall_tone, economic_outlook (improving, stable, deteriorating, uncertain, not stated), mentions_uncertainty, mentions_recession |
| Policy and framing | policy_level, government_involved, frame |
| Press releases only | communication_type (financial results, outlook or guidance, statistical release, monetary policy, policy proposal or position, investment or expansion, restructuring or job cuts, personnel, product or service, partnership or acquisition, event or service information) |

- `frame` uses the five generic news frames of Semetko and Valkenburg (2000), as in dataset.politics.germany.
- `mentions_uncertainty` and `mentions_recession` follow the idea of text-based uncertainty indices (economic policy uncertainty) and recession word counts; aggregated per week, they serve as sentiment indicators.
- `indicators` record the direction of an indicator as the text reports it, e.g. "Rising" for inflation in an article about higher inflation. Aggregated per indicator and week, they measure how the press reports the economy before and after statistical releases.
- Company names are resolved against the registry: the name as returned by the model, with or without its legal form, must equal the name or an alias of exactly one company. Other company names are stored in `other_companies`; the monthly review lists the frequent ones as candidates for the registry.
- Long vocabularies (sectors, institutions, event types, indicators, commodities, shortages, states, secondary topics) are plain strings in the response schema, with the allowed values in the field description, because a response schema with many enumerations exceeds the limit of constrained decoding of the Gemini API. The annotation keeps only values of the vocabularies.
- Input per item: title, teaser and up to 1,500 characters of lead text where permitted. Ten items per request; up to four requests at the same time.
- Up to `MAX_ANNOTATIONS_PER_RUN` (400) items are annotated per run: all press releases first, then news items in turns across the outlets, newest first. The other new items are stored without annotation, so that the item counts per source stay complete and the annotated sample can be weighted.

### 3.6 Sectors

The sector vocabulary (`Sector` in [src/schema.py](src/schema.py)) is used by the annotation, the company registry and the trade press. It groups NACE Rev. 2 divisions, so that annotated sectors can be compared with the sector statistics of the catalog:

| Sector | NACE Rev. 2 |
|---|---|
| Agriculture and food | A01–A03, C10–C12 |
| Energy and utilities | D35, E36–E39 |
| Mining and raw materials | B05–B09, C19 |
| Chemicals | C20, C22 |
| Pharmaceuticals | C21 |
| Automotive | C29 |
| Machinery and plant engineering | C28, C33 |
| Electrical and electronics | C26, C27 |
| Metals and steel | C24, C25 (except C25.4) |
| Construction | F41–F43, C23 |
| Real estate | L68 |
| Retail | G45, G47 |
| Wholesale | G46 |
| Transport and logistics | H49, H50, H52, H53 |
| Aviation | H51 |
| Telecommunications | J61 |
| Software and IT services | J58.2, J62, J63 |
| Media and entertainment | J58.1, J59, J60, R90–R93 |
| Banking and financial services | K64, K66 |
| Insurance | K65 |
| Health care | Q86–Q88, C32.5 |
| Tourism and hospitality | I55, I56, N79 |
| Defense and aerospace | C25.4, C30.3, C30.4 |
| Consumer goods | C13–C18, C31, C32 (except C32.5) |
| Public sector | O84, P85 |
| Other | all other divisions |

---

## 4. Correlation with Other Datasets

The dataset is built to be joined with [dataset.politics.germany](https://github.com/kleinnconrad/dataset.politics.germany), [dataset.technology](https://github.com/kleinnconrad/dataset.technology) and later datasets. The datasets share these conventions:

| Key | Use |
|---|---|
| `observed_at` and the event dates (period, `published_at`, `daily_views`) | Time is the main join key: aggregate all datasets to days, ISO weeks or months in UTC (or Europe/Berlin for German daily data). `observed_at` keeps the joins point-in-time correct. |
| `record_id` of news items (`news:` + hash of the normalized URL) | Both this dataset and dataset.politics.germany build the id with the same URL normalization (`src/urls.py`), so the same article has the same `record_id` in both datasets. An article that both pipelines collected can be analyzed with its political and its economic labels. |
| Outlet ids (`tagesschau`, `handelsblatt`, `welt`, `spiegel`, ...) | The outlets that both datasets collect have the same id, so outlet effects can be compared across topics. |
| Wikidata ids (`wikidata_qid`) | Companies here, technologies in dataset.technology and politicians in dataset.politics.germany carry Wikidata ids, which link entities across datasets and to external data. |
| ISO 3166 codes | Countries (`countries`, `geo` of the series) and German states (`states_concerned`, `home_state`) use ISO codes in all datasets. |
| Sectors and NACE | The sector vocabulary maps to NACE Rev. 2 (Section 3.6), the classification of the sector statistics of Eurostat and Destatis. |

Examples of cross-dataset questions:
- **Politics and economy:** do economic news with negative outlook, recession mentions or rising inflation precede poll losses of the governing parties (`polls` of dataset.politics.germany)? Do parliamentary procedures on economic policy follow periods of rising energy prices or insolvencies?
- **Technology and economy:** do AI adoption measures and job postings of dataset.technology move with the labour market and investment series here? How do the pageviews of technology companies relate to their press coverage?
- **Press across topics:** how much of the coverage of an outlet is economic versus political, and does the tone toward the government differ between economic and political articles of the same outlet?

---

## 5. Prediction Targets

The dataset is designed for questions that need long series of comparable measurements and point-in-time features. Examples:

| Target | Labels | Main features |
|---|---|---|
| GDP growth of the current and next quarter (nowcast) | `gdp_real_qoq.DE` (first release and revisions) | weekly activity index, truck toll mileage, industrial production, new orders, sentiment and surveys, press outlook and recession mentions |
| Inflation over the next months | `hicp_inflation_yoy.DE`, `cpi_inflation_yoy.DE` | import and producer prices, commodity prices, day-ahead electricity price, EUR/USD, selling price expectations, consumer price expectations, press indicator directions |
| ECB rate decisions | `ecb_deposit_facility_rate.EA` | euro area HICP and core inflation, GDP, M3, Euribor and yield curve, press reports of upcoming central bank decisions |
| Labour market turning points | `registered_unemployed.DE`, `short_time_workers.DE` | employment expectations, job vacancies, press reports of job cuts and hiring, insolvencies |
| Insolvency waves | `bankruptcy_declarations_index.DE` | corporate loan rates and credit growth, energy prices, financial stress, press insolvency events per sector |
| Sector output | sector production indices (automotive, chemicals, machinery, basic metals) | sector tone and events in the press and the trade press, shortages, energy prices |
| Supply shortages | shares of firms limited by material and labour shortages | press shortage mentions by type, commodity prices |
| Electricity prices | `day_ahead_power_price.DE` | gas and coal prices, wind and solar generation, residual load |
| Company attention and events | `wikipedia_pageviews` of a company, events in `text_annotations` | press mentions and tone, ad-hoc disclosures, corporate press releases |
| Revision behavior of statistics | revisions in `economic_series` | first release, source, survey-based indicators |

---

## 6. Sources and Fetch Rules

| Source | Access | Rate limit used | License or terms | Datasets |
|---|---|---|---|---|
| Eurostat dissemination API (SDMX 2.1) | SDMX-CSV, one request per series | 1 s | reuse authorised with acknowledgement of the source | `economic_series` |
| ECB Data Portal (SDMX 2.1) | SDMX-CSV | 1 s | reuse free of charge with acknowledgement of the source | `economic_series` |
| Deutsche Bundesbank time series database (SDMX 2.1) | SDMX-CSV | 1 s | reuse with attribution of the source; redistributed series keep the attribution of their original compiler (`original_source`) | `economic_series` |
| World Bank Commodity Price Data (Pink Sheet) | xlsx workbook, conditional request; address read from the commodity markets page | 1 s | CC BY 4.0 | `economic_series` |
| SMARD (Bundesnetzagentur) | JSON chart data files, daily resolution | 1 s | CC BY 4.0, attribution "Bundesnetzagentur \| SMARD.de" | `economic_series` |
| Wikimedia Pageviews API, Wikidata API | JSON | 0.1 s (Wikimedia), 1 s (Wikidata) | CC0 | `wikipedia_pageviews` |
| News outlets and trade publications | RSS, news sitemaps, article pages | 1 s or the crawl delay | publisher rights, metadata only | `news_items` |
| Institutions, associations, unions and companies | RSS and Atom | 1 s or the crawl delay | publisher rights, metadata only | `press_releases` |

The news outlets and press-release sources are listed in [config/sources.toml](config/sources.toml): 51 outlets (public broadcasters, national dailies and magazines, business dailies and magazines, a tabloid, online outlets, regional dailies of nine states, financial portals and 14 trade publications) and 18 press-release sources (Bundesbank, ECB, BaFin, the German Council of Economic Experts, four research institutes, two business associations, the DGB and seven corporate newsrooms). Each entry was checked for robots.txt, TDM reservation, bot protection and feed content on 2026-10-25; the comment line above each entry records the result and the time span of its feeds. `[[excluded]]` entries record 36 candidates that were checked and not admitted, with the reason. The first live run of the source review on the same day admitted the Pharmazeutische Zeitung, whose feed it found on the homepage.

**Source review.** On the first day of every month, `source_review.yml` runs [src/source_review.py](src/source_review.py) and opens a pull request with the proposed changes of `config/sources.toml`:
- **Checks of the active sources:** sources that are blocked or TDM-reserved, still broken, without a working feed, or without an economic item in 90 days (unless `keep = true`) are removed; feeds that are gone, disallowed or stale (newest item older than 180 days) are removed, permanent redirects are followed; page fetching is turned off where robots.txt states a TDM reservation in natural language or requires a crawl delay above 10 seconds.
- **Gaps:** registered companies without a press source, ordered by the number of annotated items that name them in the last 90 days, and sectors without a trade publication.
- **Search:** Gemini with Google Search proposes the official feeds of the federal economic institutions, of business associations, research institutes and trade unions, of the newsrooms of the companies of the gap list and of trade publications for the missing sectors. Each candidate is checked with the fetch rules; at most five sources are added per review. Rejected candidates become `[[excluded]]` entries; every review checks those with a temporary reason again.
- **Registries:** the report lists company names of the annotations that are not in the registry (candidates for `config/companies.toml`) and catalog series whose newest period is older than expected for their frequency (discontinued or moved series). These changes need a verified identifier or a measurement log entry and are made by hand.

**Sources as a slowly changing dimension.** Each news item and press release copies the attributes of its source when it is observed; the `added` and `removed` dates give the coverage period of every source, series and company.

**Reservations in plain text.** No host publishes a machine-readable TDMRep file, but many outlets (including all ARD broadcasters) state a reservation under § 44b UrhG in plain-text comments of their robots.txt. For these outlets, `fetch_pages` is false: their article pages are not fetched, and their items are annotated from title and teaser only. Outlets that declare a machine-readable reservation (FAZ, Lebensmittel Zeitung, fvw, energate) or block automated requests (Die Zeit, finanzen.net, several corporate newsrooms) are not included.

**Fetch rules** ([src/web.py](src/web.py)), the same as in dataset.politics.germany and dataset.technology:
- Every request identifies the pipeline with the User-Agent `GermanEconomicsDataset/0.1 (+https://github.com/kleinnconrad/dataset.economics.germany)`. No personal data is sent.
- **robots.txt** is checked for every website request (feeds, sitemaps, pages, the World Bank commodity markets page) with the longest-match rule of RFC 9309. Documented APIs and data files offered for programmatic use (Eurostat, ECB, Bundesbank, SMARD, Wikimedia, Wikidata) are called under their terms and rate limits (`respect_robots=False`).
- **Text-and-data-mining reservations** (TDMRep header, `/.well-known/tdmrep.json`, `tdm-reservation` meta tag) exclude a source (`tdm_reserved`).
- **Bot protection:** HTTP 401 or 403, a challenge page or a CAPTCHA sets a news or press source to `blocked`; a statistics collector stops with an error. No headless browser is used.
- **Pacing:** one request per second per host, longer if robots.txt sets a crawl delay; a host that requires more than 120 seconds is not fetched. Server errors, rate limits and network errors are retried twice.
- **Broken sources:** after 7 consecutive failed runs a news or press source is `broken` and is retried once a week.

**Sources that were checked and are not collected:**

| Source | Reason |
|---|---|
| Destatis GENESIS-Online API | requires a registered account; the Destatis series of the catalog are read from Eurostat and the Bundesbank, which redistribute them |
| ifo business climate, ZEW indicators, PMI | no open license for redistribution; the European Commission surveys are used instead |
| Stock prices and indices (DAX) | no free source with a license for redistribution; company attention is measured with pageviews and press coverage |
| FRED, EIA, AGSI+ (gas storage), Tankerkönig (fuel prices) | require an API key; AGSI+ and fuel prices are planned |
| SEC EDGAR | requires contact details in the User-Agent; the pipeline sends no personal data |
| Federal Ministry of Finance, Federal Ministry of Labour | robots.txt requires a crawl delay of 180 seconds |
| Eurostat release calendar feeds | disallowed by robots.txt |

---

## 7. Storage, Partitioning and Data Volume

```text
data/
├── economic_series/year=2026/month=10/economic_series_2026-10-27.json
├── news_items/year=2026/month=10/news_items_2026-10-27.json
├── ...
└── state/
    ├── seen/<dataset>.json             # written items with content hash and revision
    ├── seen/economic_series/<id>.json  # current values of every series (one shard per series)
    ├── collectors.json                 # first run, last run, failures, cursor per collector
    ├── sources.json                    # health status per news and press source
    └── run_log.jsonl                   # one line per run
```

- **Partition key:** the UTC day of the run that observed the record. A run writes at most one file per dataset; records are merged by `record_id` and `revision`.
- **Folder names:** `year=` and `month=` let DuckDB, Polars and pyarrow read a dataset as one table with partition pruning.
- **Format:** one JSON list per file with one record per line.
- **Seen stores:** the keys of news and press items are kept for 30 days; series, companies and catalog entries permanently.
- **Expected volume:** the first import writes about 12 MB of records (series history 5 MB, pageviews since 2015 7 MB) and 6 MB of state, measured in a test run on 2026-10-25. A regular run adds about 1,500 news items and press releases (about 1 MB with annotations); series revisions and pageviews add a few hundred kilobytes per week. The total growth is about 150 MB per year, dominated by news; git compresses the files to a fraction of their size.
- **Long-term plan:** when the repository approaches 1 GB, the news datasets of completed years move to a separate data repository with the same layout, or are archived as compressed Parquet files per year and dataset.

---

## 8. Repository Structure

```text
dataset.economics.germany/
├── .github/
│   ├── dependabot.yml
│   └── workflows/
│       ├── ci.yml              # lint, tests, commit messages
│       ├── notify.yml          # run summary as a commit comment that mentions the owner
│       ├── pipeline.yml        # due collectors, Tuesdays and Fridays 02:07 Europe/Berlin; backfill by hand
│       └── source_review.yml   # monthly review of the sources as a pull request
├── config/
│   ├── series.toml             # catalog of the statistical series
│   ├── companies.toml          # registry of the companies
│   └── sources.toml            # news outlets and press-release sources
├── data/                       # datasets and state, committed by the workflow
├── src/
│   ├── main.py                 # entry point
│   ├── pipeline.py             # collector order, isolation, run log
│   ├── settings.py             # environment variables
│   ├── web.py                  # HTTP client with the fetch rules
│   ├── schema.py               # record models and Gemini response models
│   ├── catalog.py              # series catalog
│   ├── companies.py            # company registry and name resolution
│   ├── sources.py              # source configuration and health rules
│   ├── content.py              # metadata and lead text of article pages
│   ├── annotation.py           # Gemini labels
│   ├── storage.py, state.py, urls.py
│   ├── generate_dataset_overview.py
│   ├── source_review.py        # monthly review of the sources and registries
│   └── collectors/
│       ├── base.py             # collector interface and run context
│       ├── series.py           # vintages of statistical series
│       ├── sdmx.py             # Eurostat, ECB, Bundesbank
│       ├── commodities.py      # World Bank Pink Sheet
│       ├── electricity.py      # SMARD
│       ├── registries.py       # series catalog and companies
│       ├── pageviews.py        # Wikipedia pageviews of the companies
│       └── feeds.py            # news, press releases, annotations
├── scripts/
│   └── run_summary.py          # run summary for notify.yml
├── tests/                      # offline tests with a fake web and a fake Gemini client
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## 9. Pipeline Run

`src/main.py` starts the run; `src/pipeline.py` runs the collectors in the order of `COLLECTOR_ORDER`:

1. **series_catalog, companies:** write new and changed entries of the registries (no requests).
2. **feeds:** read the RSS/Atom feeds and news sitemaps of all due sources; keep new economic items published within 96 hours; select up to 400 items (press releases first, then news items in turns across the outlets); fetch article pages where permitted, annotate ten items per Gemini request with up to four requests at the same time, resolve company names, and write items and annotations every 100 items; write the other new items without labels.
3. **ecb, bundesbank, eurostat:** fetch every catalog series of the provider and write the new and revised vintages.
4. **electricity:** fetch the SMARD series (all yearly files for a new series, the two newest afterwards).
5. **commodities** (weekly): download the Pink Sheet if it changed and write the new and revised series.
6. **wikipedia_pageviews** (weekly): fetch the days since the last stored day per company.
7. The workflow updates the README overview and commits `data/` and `README.md`. `notify.yml` then posts a summary of the run, with the Gemini tokens and their estimated cost, as a commit comment that mentions the repository owner.

**Run modes.** A regular run (`normal`) has a deadline of 25 minutes (`RUN_DEADLINE_MINUTES`) and a job timeout of 30 minutes. A `backfill` run imports the history of all collectors except the feeds without the weekly intervals (deadline 85 minutes, timeout 90 minutes). `shadow` and `dry-run` work on a copy of the state and commit nothing.

**Measured duration** (test runs on 2026-10-25):

| Step | First run | Later runs |
|---|---|---|
| feeds: reading 69 sources | 1 min | 1 min |
| feeds: pages and Gemini (400 items) | 6 to 8 min (estimate) | 6 to 8 min |
| ecb, bundesbank (46 series) | 1 min | 1 min |
| eurostat (143 series) | 2.5 min | 2.5 min |
| electricity (14 series) | 3 min | 0.7 min |
| commodities | 0.2 min | weekly, 0.1 min |
| wikipedia_pageviews (110 articles) | 3 min | weekly, 1 min |
| Total | about 17 to 19 min | about 12 to 15 min |

---

## 10. Failure Handling

- **A collector fails:** the error is logged, recorded in `collectors.json` and the run log, and the next collector starts. Data already written stays. The run exits with code 1.
- **A series fails** (HTTP error, invalid response): the other series continue; the failure is counted. A series that the provider no longer knows (HTTP 404) is counted as `not_found` and listed in the run log; the monthly review reports it.
- **Incomplete series response:** a response that would remove more than 5 % of the stored periods (and more than three) is not written; the next run tries again.
- **A news or press source fails:** the other sources continue; the source health rules apply (`broken`, `blocked`, `tdm_reserved`).
- **Gemini returns an unusable response:** the batch is split in halves down to single items; items without usable labels are written without annotation.
- **Gemini quota, call budget or API error:** the annotation stops; the remaining items are written without annotation. A quota or API error marks the collector as failed; reaching the call budget does not.
- **Run deadline:** after `RUN_DEADLINE_MINUTES` the collectors start no new work; a collector that stops early has the status `partial` and continues in the next run.
- **Concurrent pushes:** the workflow pulls with rebase and retries the push up to three times.

---

## 11. Measurement Log

Changes of sources, keys, filters, units and counting rules, and known breaks in the sources. Add a line for every change.

| Date | Dataset | Change |
|---|---|---|
| 2026-10-25 | all | Design of the pipeline; catalog of 238 series, registry of 110 companies, 51 outlets and 18 press sources, all verified on this day. |
| 2026-10-25 | `economic_series` | HICP from the ECOICOP version 2 dataset `prc_hicp_minr`; the version 1 datasets (`prc_hicp_manr`, `prc_hicp_midx`) end with 2025-12. Index base 2025 = 100. |
| 2026-10-25 | `economic_series` | Euro area: Eurostat code `EA` (changing composition) where the dataset has it (national accounts, HICP, house prices, energy prices, labour cost index, employment); `EA21` (21 members since 2026, computed back) for the short-term statistics, unemployment, job vacancies, business and consumer surveys and government finance, which publish only fixed compositions. ECB series use `U2` (changing composition). |
| 2026-10-25 | `economic_series` | Job vacancy rate from the NACE Rev. 2.1 dataset `jvs_q_r21` (activities B-T); the NACE Rev. 2 dataset `jvs_q_nace2` ends with 2025-Q4. Eurostat moves further short-term statistics to NACE Rev. 2.1; the monthly review reports series that stop. |
| 2026-10-25 | `economic_series` | Industry employment expectations with the code `BS-IEME-BAL`; the code `BS-IEME` ends with 2024-09. |
| 2026-10-25 | `economic_series` | Corporate loan growth: the German series uses the adjustment code `A` (`BSI.M.DE.Y.A.A20T...`), the euro area series `U`. |
| 2026-10-25 | `economic_series` | SMARD: daily resolution (daily average for the price, daily sums for load and generation); days before the day of the run only; timestamps are midnight Europe/Berlin. Nuclear generation is not collected (zero since April 2023). The day-ahead price of the bidding zone Germany/Luxembourg starts on 2018-10-01. |
| 2026-10-25 | `economic_series` | Pink Sheet: columns selected by their header names on the sheets "Monthly Prices" and "Monthly Indices", with footnote markers removed; periods `YYYYMmm` stored as `YYYY-MM`. |
| 2026-10-25 | `economic_series` | Bundesbank series that redistribute data of Destatis or the Federal Employment Agency store the source note of the Bundesbank in `original_source`. Values are stored as the Bundesbank publishes them: registered unemployed, vacancies and employment in thousands, short-time workers in persons. |
| 2026-10-25 | `news_items` | Prefilter for general outlets: economics feeds and URL sections (`ECONOMICS_PATH_TOKENS`) or terms (`ECONOMICS_TERMS`); outlets of the types business_daily, business_magazine, financial_portal and trade_press pass without the filter. |
| 2026-10-25 | `text_annotations` | Long vocabularies are strings in the response schema with the allowed values in the field description; values outside the vocabularies are dropped. Country codes UK and EL are stored as GB and GR. |

---

## 12. Implementation Status

| Part | Status |
|---|---|
| Statistical series of Eurostat, ECB, Bundesbank, World Bank Pink Sheet and SMARD as vintages | implemented |
| Series catalog and company registry with their datasets | implemented |
| Wikipedia pageviews of the companies | implemented |
| News items, press releases, Gemini annotations with company resolution | implemented |
| Monthly source review with pull requests, report of unregistered companies and stale series | implemented |
| Gas storage levels in Germany (AGSI+, free API key) | planned |
| Weekly fuel prices of the EU Weekly Oil Bulletin | planned |
| Global Supply Chain Pressure Index (after a check of its terms) | planned |
| Corporate filings (ESEF annual reports of listed companies) | planned |
| Story clusters across outlets (`story_id`, `story_size`) | planned |
| Feature tables for model training with point-in-time joins of the series vintages (`scripts/build_features.py`) | planned |
| Review sheet for the annotation and a hand-labelled sample to measure agreement | planned |
