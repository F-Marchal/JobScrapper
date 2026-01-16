ORGS = chu-mpt cirad cnrs france-genomique ifremer inrae inserm ird sanofi sfbi
.PHONY: full_scraping $(addprefix scrap-,$(ORGS))

WORKDIR = ./Workdir
FLAT_PATH = ./Workdir/flat_jobs_files
DATE = $(shell date +%Y-%m-%d-%H-%M-%S)
YESTERDAY = $(shell date -d "yesterday" "+%Y-%m-%d")

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

FOLDER ?= ./job_scrapper
cleancode:
	poetry run black $(FOLDER) # Refomate code
	poetry run isort  $(FOLDER)  # Sort dependances
	poetry run mypy  $(FOLDER)  # statick typing
	poetry run pylint  $(FOLDER)  # Coding Standard

cleantestcode:
	poetry run black ./tests/ # Refomate code
	poetry run isort  ./tests/  # Sort dependances
	poetry run mypy  ./tests/  # statick typing
	poetry run pylint  ./tests/  # Coding Standard


example_cmd = poetry run job-scrapper database request \
        -c url -c localisation -c contract -c title -c origin \
        -d 'Montpellier, france' -d 'Lyon, france' \
        -k Bioinformatic -k Bioinformatic_enhanced -k Informatic \
        -o Bioinformatic -o Bioinformatic_enhanced -o Informatic -o contract -o localisation -o 'Montpellier, france' -o 'Lyon, france' \

my_request:
	$(example_cmd)

my_request_alive:
	$(example_cmd) -t "last sighting::>::$(YESTERDAY)"

my_request_new:
	$(example_cmd) -t "first sighting::>::$(YESTERDAY)"