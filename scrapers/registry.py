from scrapers.agro import AgroBankScraper
from scrapers.aloqa import AloqabankScraper
from scrapers.asaka import AsakabankScraper
from scrapers.hamkor import HamkorBankScraper
from scrapers.infinbank import InfinBankScraper
from scrapers.ipakyuli import IpakYuliBankScraper
from scrapers.ipoteka import IpotekaBankScraper
from scrapers.kapital import KapitalBankScraper
from scrapers.mikrokreditbank import MikrokreditBankScraper
from scrapers.nbu import NBUScraper
from scrapers.sqb import SQBScraper
from scrapers.tenge import TengeBankScraper
from scrapers.turon import TuronBankScraper
from scrapers.xalqbank import XalqBankScraper

ALL_SCRAPERS = [
    SQBScraper,
    NBUScraper,
    IpotekaBankScraper,
    HamkorBankScraper,
    AgroBankScraper,
    InfinBankScraper,
    MikrokreditBankScraper,
    IpakYuliBankScraper,
    AloqabankScraper,
    XalqBankScraper,
    AsakabankScraper,
    KapitalBankScraper,
    TuronBankScraper,
    TengeBankScraper,
]
