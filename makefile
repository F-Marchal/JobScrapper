ORGS = chu-mpt cirad cnrs france-genomique ifremer inrae inserm ird sanofi sfbi
.PHONY: full_scraping $(addprefix scrap-,$(ORGS))

WORKDIR = ./Workdir
FLAT_PATH = ./Workdir/flat_jobs_files
DATE = $(shell date +%Y-%m-%d-%H-%M-%S)

CMD = mkdir -p $(FLAT_PATH) && \
      poetry run job-scrapper -w $(WORKDIR) scrap --save-job-page \
      --result-file "$(FLAT_PATH)/$(@:scrap-%=%)-$(DATE).job" $(@:scrap-%=%)

scrap-chu-mpt: ; $(CMD)
scrap-cirad: ; $(CMD)
scrap-cnrs: ; $(CMD)
scrap-france-genomique: ; $(CMD)
scrap-ifremer: ; $(CMD)
scrap-inrae: ; $(CMD)
scrap-inserm: ; $(CMD)
scrap-ird: ; $(CMD)
scrap-sanofi: ; $(CMD)
scrap-sfbi: ; $(CMD)



full_scraping: $(addprefix scrap-,$(ORGS))

cleancode:
	poetry run black ./job_scrapper/ # Refomate code
	poetry run isort  ./job_scrapper/  # Sort dependances
	poetry run mypy  ./job_scrapper/  # statick typing
	poetry run pylint  ./job_scrapper/  # Coding Standard
