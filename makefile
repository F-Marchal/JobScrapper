cleancode:
	poetry run black ./job_scrapper/ # Refomate code
	poetry run isort  ./job_scrapper/  # Sort dependances
	poetry run mypy  ./job_scrapper/  # statick typing
	poetry run pylint  ./job_scrapper/  # Coding Standard


ORGS = chu-mpt cirad cnrs france-genomique ifremer inrae inserm ird sanofi sfbi
WORKDIR = "./Workdir"
FLAT_PATH = "./Workdir/flat_jobs_files/"

full_scraping:
	mkdir -p $(FLAT_PATH)
	for org in $(ORGS); do \
		poetry run job-scrapper -w $(WORKDIR) scrap --save-job-page \
		--result-file "$(FLAT_PATH)$$org-`date +%Y-%m-%d-%H-%M-%S`.job" $$org; \
	done

test:
	file_name="$$org-`date +%Y-%m-%d-%H-%M-%S`.json"
	echo "$$org-`date +%Y-%m-%d-%H-%M-%S`.job"
