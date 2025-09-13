# Skeleton class
from .scrapper_skeleton.scrapper_skeleton import JobScrapperSkeleton
from .scrapper_skeleton.pdf_jobs import PdfJobBaseScrapper

# Scrapper class
from .scrap_job_from.chu_mtp import CHUMtpScrapper
from .scrap_job_from.cirad import CiradScrapper
from .scrap_job_from.cnrs import CNRScrapper
from .scrap_job_from.inrae import INRAEScrapper
from .scrap_job_from.inserm import InsermScrapper
from .scrap_job_from.ird import IRDScrapper
from .scrap_job_from.sanofi import SanofiScrapper
from .scrap_job_from.sfbi import SBIScrapper