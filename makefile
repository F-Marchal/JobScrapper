cleancode:
	poetry run black ./job_scrapper/ # Refomate code
	poetry run isort  ./job_scrapper/  # Sort dependances
	poetry run mypy  ./job_scrapper/  # statick typing
	poetry run pylint  ./job_scrapper/  # Coding Standard
