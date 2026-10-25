"""
Defines the Pydantic models of the German economics dataset.

The models that Gemini fills (``ItemAnnotation`` and its parts) are separate
from the records written to disk (subclasses of ``RecordBase``).
Vocabularies are ``Literal`` aliases, because google-genai drops the field
descriptions of ``Enum`` classes when it builds the response schema. All
fields of the models sent to Gemini are required; absence is expressed with
"Not stated", "Not applicable", an empty list or null.
"""
import types
import typing
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0"

# ISO 3166-2 codes of the German states
StateCode = Literal["DE-BW", "DE-BY", "DE-BE", "DE-BB", "DE-HB", "DE-HH", "DE-HE", "DE-MV", "DE-NI", "DE-NW",
                    "DE-RP", "DE-SL", "DE-SN", "DE-ST", "DE-SH", "DE-TH"]
# Level of an issuer of press releases: Germany, a state, the European Union or an international organization
Jurisdiction = Literal["DE", StateCode, "EU", "INT"]

# ---------------------------------------------------------------------------
# Statistical series
# ---------------------------------------------------------------------------

Provider = Literal["eurostat", "ecb", "bundesbank", "worldbank_cmo", "smard"]
# D daily, W weekly, M monthly, Q quarterly, S half-yearly, A annual
Frequency = Literal["D", "W", "M", "Q", "S", "A"]
SeriesTopic = Literal["output_and_demand", "production_and_orders", "high_frequency_activity", "prices",
                      "wages_and_labour_costs", "labour_market", "interest_rates", "money_and_credit",
                      "exchange_rates", "financial_stress", "public_finances", "trade", "sentiment_and_surveys",
                      "shortages", "housing", "business_demography", "commodities", "energy"]

# ---------------------------------------------------------------------------
# News, press releases and companies
# ---------------------------------------------------------------------------

OutletType = Literal["public_broadcaster_national", "public_broadcaster_regional", "national_daily",
                     "weekly_magazine", "regional_daily", "tabloid", "online_only", "business_daily",
                     "business_magazine", "financial_portal", "trade_press"]
PaywallModel = Literal["free", "mixed", "hard"]
ActorType = Literal["federal_government", "federal_ministry", "state_government", "central_bank",
                    "statistical_office", "public_agency", "eu_institution", "international_organization",
                    "research_institute", "business_association", "trade_union", "company"]
ContentBasis = Literal["title_only", "title_teaser", "lead_text"]
Channel = Literal["rss", "news_sitemap"]
ItemDataset = Literal["news_items", "press_releases"]

# Economic sectors, used by the annotation, the company registry and the trade press. The NACE Rev. 2
# divisions of every sector are listed in project_architecture.md.
Sector = Literal["Agriculture and food", "Energy and utilities", "Mining and raw materials", "Chemicals",
                 "Pharmaceuticals", "Automotive", "Machinery and plant engineering", "Electrical and electronics",
                 "Metals and steel", "Construction", "Real estate", "Retail", "Wholesale",
                 "Transport and logistics", "Aviation", "Telecommunications", "Software and IT services",
                 "Media and entertainment", "Banking and financial services", "Insurance", "Health care",
                 "Tourism and hospitality", "Defense and aerospace", "Consumer goods", "Public sector", "Other"]

EconomicTopic = Literal["Growth and business cycle", "Inflation and prices", "Monetary policy and interest rates",
                        "Public finances and taxes", "Labour market and wages", "Energy",
                        "Raw materials and commodities", "Trade and tariffs", "Supply chains and shortages",
                        "Industry and manufacturing", "Financial markets", "Banking and insurance",
                        "Corporate strategy and results", "Real estate and construction", "Consumption and retail",
                        "Digital economy and technology", "Climate and environment", "Social security and pensions",
                        "Regulation and competition", "Other"]
EventType = Literal["Statistical release", "Economic forecast", "Central bank decision", "Earnings report",
                    "Profit warning", "Guidance change", "Merger or acquisition", "Investment or expansion",
                    "Plant closure or relocation", "Job cuts", "Hiring", "Insolvency or restructuring",
                    "Strike or labour dispute", "Wage agreement", "Price increase", "Price decrease",
                    "Supply shortage", "Supply chain disruption", "Tariff or trade dispute", "Sanctions",
                    "Legislation or regulation", "Subsidy or state aid", "Tax change", "Budget decision",
                    "Market turmoil", "Capital market transaction", "Management change", "Product launch",
                    "Legal or antitrust case", "Energy supply event", "Other"]
EventStatus = Literal["Announced or planned", "Ongoing", "Concluded", "Not applicable"]
Indicator = Literal["GDP or growth", "Inflation", "Producer or import prices", "Interest rates", "Unemployment",
                    "Employment", "Wages", "Industrial production", "New orders", "Exports or imports",
                    "Business sentiment", "Consumer sentiment", "Retail sales", "Insolvencies", "House prices",
                    "Public debt or deficit", "Stock market", "Exchange rate", "Energy prices", "Commodity prices",
                    "Corporate earnings", "Other"]
Direction = Literal["Rising", "Falling", "Unchanged", "Not stated"]
Commodity = Literal["Crude oil", "Fuels", "Natural gas", "Electricity", "Coal", "Hydrogen", "Copper", "Aluminium",
                    "Steel and iron ore", "Nickel", "Lithium", "Rare earths", "Gold", "Silver", "Wheat and grains",
                    "Coffee", "Cocoa", "Sugar", "Fertilizers", "Wood", "Other"]
Shortage = Literal["Raw materials", "Energy", "Semiconductors and electronics", "Intermediate goods",
                   "Skilled workers", "Workers in general", "Housing", "Transport capacity", "Medicines", "Food",
                   "Other"]
Institution = Literal["European Central Bank", "Deutsche Bundesbank", "Federal government",
                      "Federal Ministry for Economic Affairs", "Federal Ministry of Finance",
                      "Federal Ministry of Labour", "Federal Employment Agency", "Federal Statistical Office",
                      "Federal Cartel Office", "BaFin", "Federal Network Agency", "State government",
                      "European Commission", "Other EU institution", "German Council of Economic Experts",
                      "Economic research institute", "Business association", "Trade union", "IMF", "OECD",
                      "US Federal Reserve", "US government", "Chinese government", "Other"]
Outlook = Literal["Improving", "Stable", "Deteriorating", "Uncertain", "Not stated"]
PolicyLevel = Literal["Municipal", "State", "Federal", "European Union", "International", "Not applicable"]
ArticleType = Literal["News", "Opinion", "Interview", "Analysis", "Live blog", "Explainer", "Press release",
                      "Other"]
Tone = Literal["Positive", "Neutral", "Negative", "Mixed"]
CompanyRole = Literal["Subject", "Affected", "Commentator"]
# Generic news frames of Semetko and Valkenburg (2000), as in dataset.politics.germany
Frame = Literal["Conflict", "Economic consequences", "Responsibility", "Human interest", "Morality",
                "No dominant frame"]
CommunicationType = Literal["Financial results", "Outlook or guidance", "Statistical release", "Monetary policy",
                            "Policy proposal or position", "Investment or expansion", "Restructuring or job cuts",
                            "Personnel", "Product or service", "Partnership or acquisition",
                            "Event or service information", "Other", "Not applicable"]


# ---------------------------------------------------------------------------
# Models filled by Gemini
# ---------------------------------------------------------------------------
# Long vocabularies are plain strings in these models, with the allowed values in the description:
# a response schema with many enumerations exceeds the limit of constrained decoding of the Gemini API.
# The annotation keeps only values of the vocabulary (annotation.clean_annotation); the stored
# records validate them against the Literal types.

def allowed(vocabulary: object) -> str:
    """Returns the values of a Literal vocabulary as text for a field description.

    Args:
        vocabulary: A ``Literal`` alias.

    Returns:
        str: For example ``Allowed values: Positive; Neutral; Negative; Mixed.``
    """
    return "Allowed values: " + "; ".join(str(value) for value in typing.get_args(vocabulary)) + "."


class CompanyMention(BaseModel):
    """A company that the text refers to, as filled by the model."""
    name: str = Field(description="Common name of the company or corporate group, e.g. 'Volkswagen', 'Deutsche Bank', 'Lidl'. Only businesses; no government bodies, associations, unions or research institutes.")
    role: CompanyRole = Field(description="Subject if the company acts, reports or is the main topic; Affected if it is affected by an event or decision; Commentator if it only comments.")
    tone: Tone = Field(description="How the text presents this company.")


class IndicatorMention(BaseModel):
    """An economic indicator whose value or development the text reports."""
    indicator: str = Field(description="The indicator. " + allowed(Indicator))
    direction: Direction = Field(description="Development of the indicator as reported in the text.")


class CommodityMention(BaseModel):
    """A commodity whose price, supply or demand the text discusses."""
    commodity: str = Field(description="The commodity. " + allowed(Commodity))
    price_direction: Direction = Field(description="Development of its price as reported in the text; 'Not stated' if the text reports no price development.")


class UpcomingEvent(BaseModel):
    """A future event that the text names with a date."""
    event_type: str = Field(description="Type of the upcoming event. " + allowed(EventType))
    date: str = Field(description="Date of the event (YYYY-MM-DD). Only events with a stated day.")


class ItemAnnotation(BaseModel):
    """The labels of one article or press release."""
    item_number: int = Field(description="Number of the item in the request, starting at 1.")
    is_economic: bool = Field(description="True if the item is about the economy: business cycle, prices, labour market, companies, sectors, markets, trade, energy, public finances or economic policy.")
    topic: EconomicTopic = Field(description="Main economic topic of the item. 'Other' if the item is not economic.")
    topics_secondary: list[str] = Field(description="Further clearly addressed economic topics, at most two, with the values of topic. Empty list if none.")
    issue_detail: Optional[str] = Field(description="The specific issue in one to five words, e.g. 'Gas storage levels' or 'Job cuts at suppliers'. Null if not economic.")
    article_type: ArticleType = Field(description="Form of the item, judged from the title and text, e.g. 'Opinion' for commentaries, 'Interview' for interviews.")
    sectors: list[str] = Field(description="Economic sectors the item is mainly about, at most three. Empty list for items about the economy as a whole. " + allowed(Sector))
    companies: list[CompanyMention] = Field(description="Every company or corporate group the item refers to, each once.")
    institutions: list[str] = Field(description="Public institutions, associations and organizations that act, decide or comment in the item, each once. " + allowed(Institution))
    countries: list[str] = Field(description="Countries the item is mainly about, as ISO 3166-1 alpha-2 codes, e.g. DE, US, CN. Empty list if no country is concerned.")
    states_concerned: list[str] = Field(description="German states the item is mainly about, as ISO 3166-2 codes (DE-BW, DE-BY, DE-BE, DE-BB, DE-HB, DE-HH, DE-HE, DE-MV, DE-NI, DE-NW, DE-RP, DE-SL, DE-SN, DE-ST, DE-SH, DE-TH). Empty list for national or international items.")
    event_types: list[str] = Field(description="Types of economic events the item reports. Empty list if none. " + allowed(EventType))
    event_status: EventStatus = Field(description="Whether the main event is announced or planned, ongoing or concluded. 'Not applicable' without an event.")
    indicators: list[IndicatorMention] = Field(description="Economic indicators whose current value or development the item reports, each once.")
    commodities: list[CommodityMention] = Field(description="Commodities whose price, supply or demand the item discusses, each once.")
    shortages: list[str] = Field(description="Shortages that the item reports: of goods, energy, workers, housing or capacity. Empty list if none. " + allowed(Shortage))
    overall_tone: Tone = Field(description="Overall tone of the item.")
    economic_outlook: Outlook = Field(description="Expected development of the economy, sector or company the item is about, as stated or clearly implied in the text. 'Not stated' if the item contains no expectation.")
    mentions_uncertainty: bool = Field(description="True if the text refers to uncertainty about the economy or economic policy (e.g. 'Unsicherheit', 'ungewiss', 'uncertainty').")
    mentions_recession: bool = Field(description="True if the text uses the word recession or refers to a recession (e.g. 'Rezession', 'Wirtschaftskrise', 'Abschwung').")
    policy_level: PolicyLevel = Field(description="Main level of economic policy the item addresses. 'Not applicable' if no policy is addressed.")
    government_involved: bool = Field(description="True if the federal government, a state government or one of their members acts or is addressed.")
    frame: Frame = Field(description="Dominant frame of the item.")
    upcoming_events: list[UpcomingEvent] = Field(description="Future economic events named with a date (statistical releases, central bank meetings, earnings dates, wage negotiations, deadlines, summits). Empty list if none.")
    communication_type: CommunicationType = Field(description="For press releases: the main purpose of the release. 'Not applicable' for news articles.")


class AnnotationBatch(BaseModel):
    """The model response for a batch of items."""
    items: list[ItemAnnotation] = Field(description="One entry per item of the request, in the order of the request.")


# ---------------------------------------------------------------------------
# Stored records
# ---------------------------------------------------------------------------

class RecordBase(BaseModel):
    """Fields that every record of the dataset has."""
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(description="Stable id of the item. Together with revision it identifies a record.")
    revision: int = Field(default=0, description="0 for the first observation; incremented each time the source changes the item.")
    dataset: str = Field(description="Name of the dataset.")
    schema_version: str = Field(default=SCHEMA_VERSION, description="Version of the record schema.")
    observed_at: datetime = Field(description="UTC time at which the pipeline observed this version of the item. Filtering observed_at <= t gives the state of knowledge at time t.")
    source_id: str = Field(description="Id of the source (API, file, outlet or press source).")
    source_url: Optional[str] = Field(description="URL of the item or of the API resource it was read from.")
    license: str = Field(description="License or terms of the source.")
    backfilled: bool = Field(description="True if the item is older than the start of collection for its dataset, so that observed_at does not reflect when it became public.")


class SeriesCatalogRecord(RecordBase):
    """An entry of the series catalog, recorded when it appears or changes."""
    series_id: str = Field(description="Stable id of the series: concept and geo, e.g. 'hicp_inflation_yoy.DE'.")
    concept: str = Field(description="What the series measures, independent of the country, e.g. 'hicp_inflation_yoy'.")
    name: str = Field(description="Name of the series.")
    topic: SeriesTopic = Field(description="Topic group of the series.")
    geo: str = Field(description="Country or area: Eurostat country code (DE, FR, ...), EA for the euro area (changing composition), EU27_2020, or WLD for world prices.")
    frequency: Frequency = Field(description="Frequency of the periods: D daily, W weekly, M monthly, Q quarterly, S half-yearly, A annual.")
    unit: str = Field(description="Unit of the values, e.g. 'percent change on the same period of the previous year'.")
    provider: Provider = Field(description="Organization and interface the series is read from.")
    provider_flow: str = Field(description="Dataset or dataflow of the provider, e.g. 'prc_hicp_minr' or 'FM'.")
    provider_key: str = Field(description="Key of the series at the provider, e.g. an SDMX series key.")
    added: date = Field(description="Day on which the series was added to the catalog; start of collection.")
    removed: Optional[date] = Field(description="Day on which the series was removed from the catalog; end of collection.")
    removed_reason: Optional[str] = Field(description="Why the series was removed.")


class EconomicSeriesRecord(RecordBase):
    """A vintage of a statistical series: all values at the first observation, then the added, revised and removed periods."""
    series_id: str = Field(description="Id of the series in the catalog.")
    concept: str = Field(description="What the series measures, independent of the country.")
    topic: SeriesTopic = Field(description="Topic group of the series.")
    geo: str = Field(description="Country or area of the series.")
    frequency: Frequency = Field(description="Frequency of the periods.")
    unit: str = Field(description="Unit of the values.")
    provider: Provider = Field(description="Organization and interface the series is read from.")
    provider_flow: str = Field(description="Dataset or dataflow of the provider.")
    provider_key: str = Field(description="Key of the series at the provider.")
    provider_title: Optional[str] = Field(description="Title of the series as given by the provider, if the response contains one.")
    original_source: Optional[str] = Field(description="Original compiler of the data if the provider redistributes it, e.g. 'Statistisches Bundesamt' for a Bundesbank series.")
    values: dict[str, float] = Field(description="Values by period (YYYY-MM-DD, YYYY-Www, YYYY-MM, YYYY-Qn, YYYY-Sn or YYYY). Revision 0 holds all periods of the series; a later revision only the periods that were added or whose value changed.")
    removed_periods: list[str] = Field(description="Periods whose value disappeared at the provider since the previous revision.")
    first_period: Optional[str] = Field(description="First period of the complete series after this revision.")
    last_period: Optional[str] = Field(description="Last period of the complete series after this revision.")
    observations: int = Field(description="Number of periods of the complete series after this revision.")
    source_updated: Optional[datetime] = Field(description="Last update of the dataset at the provider (UTC), if the provider states it.")


class CompanyRecord(RecordBase):
    """An entry of the company registry, recorded when it appears or changes."""
    company_id: str = Field(description="Stable id of the company in the registry, e.g. 'volkswagen'.")
    name: str = Field(description="Name of the company or corporate group.")
    aliases: list[str] = Field(description="Further names under which the annotation resolves the company, e.g. brands or former names.")
    sector: Sector = Field(description="Main sector of the company.")
    country: str = Field(description="Country of the headquarters (ISO 3166-1 alpha-2).")
    listed: bool = Field(description="Whether the shares of the company are listed on a stock exchange.")
    isin: Optional[str] = Field(description="ISIN of the main share line of a listed company.")
    wikidata_qid: Optional[str] = Field(description="Wikidata id of the company.")
    added: date = Field(description="Day on which the company was added to the registry.")
    removed: Optional[date] = Field(description="Day on which the company was removed from the registry.")
    removed_reason: Optional[str] = Field(description="Why the company was removed.")


class PageviewRecord(RecordBase):
    """Daily views of the German Wikipedia article of a registered company."""
    company_id: str = Field(description="Id of the company in the registry.")
    wikipedia_project: str = Field(description="Wikipedia edition, de.wikipedia.")
    wikipedia_title: str = Field(description="Title of the article at the time of the request.")
    wikidata_qid: str = Field(description="Wikidata id from which the article was resolved.")
    daily_views: dict[date, int] = Field(description="Views by human users per day (UTC), for the days since the previous record.")


class NewsItemRecord(RecordBase):
    """Metadata of one news article. The text is not stored."""
    outlet_id: str = Field(description="Id of the outlet.")
    outlet_type: OutletType = Field(description="Type of the outlet.")
    owner_group: str = Field(description="Publisher group of the outlet, or 'public' for public broadcasters.")
    home_state: Optional[StateCode] = Field(description="State of a regional outlet; null for national outlets.")
    outlet_sector: Optional[Sector] = Field(description="Sector of a trade press outlet; null for general outlets.")
    channel: Channel = Field(description="Where the article was found: RSS/Atom feed or news sitemap.")
    url: str = Field(description="URL of the article.")
    canonical_url: Optional[str] = Field(description="Canonical URL declared by the article page.")
    title: str = Field(description="Title of the article.")
    published_at: Optional[datetime] = Field(description="Publication time (UTC).")
    updated_at: Optional[datetime] = Field(description="Last modification time from the article page (UTC).")
    section: Optional[str] = Field(description="Section of the outlet, from the page or the feed.")
    feed_categories: list[str] = Field(description="Categories of the item in the feed.")
    keywords: list[str] = Field(description="Keywords from the article page or the news sitemap.")
    jsonld_type: Optional[str] = Field(description="schema.org type of the article page, e.g. NewsArticle or OpinionNewsArticle.")
    is_agency_copy: Optional[bool] = Field(description="True if the article is credited to a news agency (dpa, AFP, Reuters, epd, KNA, AP). Null without page data.")
    author_count: Optional[int] = Field(description="Number of named authors. Author names are not stored. Null without page data.")
    word_count: Optional[int] = Field(description="Word count from the article page. Null if not given.")
    is_paywalled: Optional[bool] = Field(description="True if the page marks the article as not accessible for free. Null without page data.")
    has_video: Optional[bool] = Field(description="True if the article page embeds a video. Null without page data.")
    content_basis: ContentBasis = Field(description="Text available for the annotation: title only, title and teaser, or lead text of the page.")


class PressReleaseRecord(RecordBase):
    """Metadata of one press release. The text is not stored."""
    press_source_id: str = Field(description="Id of the press source.")
    actor_type: ActorType = Field(description="Type of the issuing actor.")
    company_id: Optional[str] = Field(description="Registry id of an issuing company; null for other actors.")
    jurisdiction: Jurisdiction = Field(description="Level of the issuer: DE, a state (ISO 3166-2), EU or INT.")
    url: str = Field(description="URL of the press release.")
    canonical_url: Optional[str] = Field(description="Canonical URL declared by the page.")
    title: str = Field(description="Title of the press release.")
    published_at: Optional[datetime] = Field(description="Publication time (UTC).")
    feed_categories: list[str] = Field(description="Categories of the item in the feed.")
    content_basis: ContentBasis = Field(description="Text available for the annotation.")


class TextAnnotationRecord(RecordBase):
    """Gemini labels of one news article or press release."""
    item_dataset: ItemDataset = Field(description="Dataset of the annotated item.")
    item_id: str = Field(description="record_id of the annotated item.")
    model: str = Field(description="Gemini model that produced the labels.")
    extraction_hash: str = Field(description="Hash of the prompt, response schema and model settings. Labels with the same hash were produced under the same conditions.")
    content_basis: ContentBasis = Field(description="Text the model saw: title only, title and teaser, or lead text.")
    is_economic: bool = Field(description="Whether the item is about the economy.")
    topic: EconomicTopic = Field(description="Main economic topic.")
    topics_secondary: list[EconomicTopic] = Field(description="Further economic topics.")
    issue_detail: Optional[str] = Field(description="Specific issue in a few words.")
    article_type: ArticleType = Field(description="Form of the item.")
    sectors: list[Sector] = Field(description="Sectors the item is mainly about.")
    mentioned_companies: list[str] = Field(description="Registry ids of the named companies that are in the company registry.")
    company_roles: dict[str, CompanyRole] = Field(description="Role of each resolved company, by registry id.")
    company_tone: dict[str, Tone] = Field(description="Tone toward each resolved company, by registry id.")
    other_companies: list[str] = Field(description="Names of further companies that are not in the registry, as returned by the model.")
    institutions: list[Institution] = Field(description="Institutions that act, decide or comment.")
    countries: list[str] = Field(description="Countries the item is mainly about (ISO 3166-1 alpha-2).")
    states_concerned: list[StateCode] = Field(description="German states the item is mainly about.")
    event_types: list[EventType] = Field(description="Types of economic events reported.")
    event_status: EventStatus = Field(description="Stage of the main event.")
    indicators: dict[str, Direction] = Field(description="Reported indicators with their reported direction.")
    commodities: dict[str, Direction] = Field(description="Discussed commodities with the reported direction of their price.")
    shortages: list[Shortage] = Field(description="Reported shortages.")
    overall_tone: Tone = Field(description="Overall tone of the item.")
    economic_outlook: Outlook = Field(description="Expected development as stated in the item.")
    mentions_uncertainty: bool = Field(description="Whether the item refers to economic or economic policy uncertainty.")
    mentions_recession: bool = Field(description="Whether the item refers to a recession.")
    policy_level: PolicyLevel = Field(description="Main level of economic policy addressed.")
    government_involved: bool = Field(description="Whether a government or its members act or are addressed.")
    frame: Frame = Field(description="Dominant news frame (Semetko and Valkenburg).")
    upcoming_events: list[dict[str, str]] = Field(description="Future events with event_type and date (YYYY-MM-DD).")
    communication_type: CommunicationType = Field(description="Purpose of a press release; 'Not applicable' for news.")


DATASET_MODELS: dict[str, type[RecordBase]] = {
    "economic_series": EconomicSeriesRecord,
    "series_catalog": SeriesCatalogRecord,
    "news_items": NewsItemRecord,
    "press_releases": PressReleaseRecord,
    "text_annotations": TextAnnotationRecord,
    "companies": CompanyRecord,
    "wikipedia_pageviews": PageviewRecord,
}

# Models whose text form goes into the extraction hash
ANNOTATION_MODELS: tuple[type[BaseModel], ...] = (
    CompanyMention, IndicatorMention, CommodityMention, UpcomingEvent, ItemAnnotation, AnnotationBatch,
)


def _describe_type(annotation: object) -> str:
    """Returns a text form of a type annotation that is the same on all supported Python versions.

    Args:
        annotation: A type annotation of a model field.

    Returns:
        str: For example ``list[CompanyMention]`` or ``Union[NoneType,str]``.
    """
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin is Literal:
        return "Literal[" + ",".join(repr(arg) for arg in args) + "]"
    if origin is typing.Union or origin is types.UnionType:
        return "Union[" + ",".join(sorted(_describe_type(arg) for arg in args)) + "]"
    if origin is list:
        return "list[" + _describe_type(args[0]) + "]"
    if origin is dict:
        return "dict[" + _describe_type(args[0]) + "," + _describe_type(args[1]) + "]"
    if isinstance(annotation, type):
        return annotation.__name__
    return repr(annotation)


def describe_models(models: typing.Iterable[type[BaseModel]], include_descriptions: bool) -> str:
    """Returns a canonical text form of models.

    The text lists every field with its type and whether it is required. It is
    used for the extraction hash (annotation models, with descriptions) and for
    the schema snapshot test (all models, without descriptions).

    Args:
        models: The models to describe.
        include_descriptions: Whether to include the field descriptions.

    Returns:
        str: One line per model and per field.
    """
    lines = []
    for model in models:
        lines.append(model.__name__)
        for name, field in model.model_fields.items():
            line = f"  {name}: {_describe_type(field.annotation)} required={field.is_required()}"
            if include_descriptions:
                line += f" description={field.description!r}"
            lines.append(line)
    return "\n".join(lines)
