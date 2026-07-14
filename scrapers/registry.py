from scrapers.agro import AgroBankScraper
from scrapers.hamkor import HamkorBankScraper
from scrapers.infinbank import InfinBankScraper
from scrapers.ipakyuli import IpakYuliBankScraper
from scrapers.ipoteka import IpotekaBankScraper
from scrapers.mikrokreditbank import MikrokreditBankScraper
from scrapers.nbu import NBUScraper
from scrapers.sqb import SQBScraper

ALL_SCRAPERS = [
    SQBScraper,
    NBUScraper,
    IpotekaBankScraper,
    HamkorBankScraper,
    AgroBankScraper,
    InfinBankScraper,
    MikrokreditBankScraper,
    IpakYuliBankScraper,
]
