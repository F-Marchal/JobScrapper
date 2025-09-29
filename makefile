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

example_request:
	poetry run job-scrapper database request \
		-c origin -c contract -c url\
		-d 'Montpellier, France<100' \
		-cb '%CHERCHEUR%' -cb '%STAGE%' -cb '%DOCTOR%' -cb '%POSTDOC%' -cb "%THÈSE%" \
		--file "last_request.tsv" \
		-o "Montpellier_France_km" -o contract  -o "Bioinformatic_enhanced_occurence" -o "Bioinformatic_occurence" \
		-k "Bioinformatic" -k "Bioinformatic_enhanced>0"