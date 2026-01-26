# ORGS = chu-mpt cirad cnrs france-genomique ifremer inrae inserm ird sanofi sfbi
# .PHONY: full_scraping $(addprefix scrap-,$(ORGS))
#
# WORKDIR = ./Workdir
# FLAT_PATH = ./Workdir/flat_jobs_files
# DATE = $(shell date +%Y-%m-%d-%H-%M-%S)
# YESTERDAY = $(shell date -d "yesterday" "+%Y-%m-%d")
#
# CMD = mkdir -p $(FLAT_PATH) && \
# 	 poetry run job-scrapper -w $(WORKDIR) scrap --save-job-page \
# 	 --result-file "$(FLAT_PATH)/$(@:scrap-%=%)-$(DATE).job" $(@:scrap-%=%)
#
# scrap-chu-mpt: ; $(CMD)
# scrap-cirad: ; $(CMD)
# scrap-cnrs: ; $(CMD)
# scrap-france-genomique: ; $(CMD)
# scrap-ifremer: ; $(CMD)
# scrap-inrae: ; $(CMD)
# scrap-inserm: ; $(CMD)
# scrap-ird: ; $(CMD)
# scrap-sanofi: ; $(CMD)
# scrap-sfbi: ; $(CMD)
#
#
#
#
# full_scraping: $(addprefix scrap-,$(ORGS))





example_cmd = poetry run job-scrapper offers list \
        -c url -c localisation -c contract -c title -c origin \
        -d 'Montpellier, france' \
        -k Bioinformatic -k Bioinformatic_enhanced -k Informatic \
        -o Bioinformatic -o Bioinformatic_enhanced -o Informatic -o contract -o localisation -o 'Montpellier, france' \

my_request:
	$(example_cmd)

my_request_alive:
	$(example_cmd) -t "last sighting::>::$(YESTERDAY)"

my_request_new:
	$(example_cmd) -t "first sighting::>::$(YESTERDAY)"

# ============================
# Keywords rules (examples)
# ============================
add_keyword: add_keyword_Informatic add_keyword_Bioinformatic add_keyword_Pipeline add_keyword_IA add_keyword_Python add_keyword_Molecular_biology add_keyword_Bioinformatic_enhanced


add_keyword_Informatic:
	job-scrapper configure keywords add -y Informatic \
		"Informatique" "Informatic" "Scripting" "Conda" "Poetry" "Docker" "Singularity" "HPC"

add_keyword_Bioinformatic:
	job-scrapper configure keywords add -y Bioinformatic \
		"Bioinformatique" "Bio-informatique" "Bioinformatic" "Bio-informatic" \
		"Computational biology" "Biologie computationnelle" "HPC" \
		"Biologie numérique" "Bioinformaticien" "Bio-informaticien" \
		"Bioinformatician" "Biocomputer"

add_keyword_Pipeline:
	job-scrapper configure keywords add -y Pipeline \
		"Pipeline" "Nextflow" "Snakemake"

add_keyword_IA:
	job-scrapper configure keywords add -y IA \
		"IA" "LLM" "Machine learning" "Apprentissage automatique" \
		"Deep learning" "Reseaux de neurone" "Réseaux de neurone" \
		"Neural network" "Traitement du langage naturel" "NLP" \
		"Natural Language Processing" "Large language model" \
		"PyTorch" "TensorFlow"

add_keyword_Python:
	job-scrapper configure keywords add -y Python \
		"Python" "PyTorch" "PyMOL" "Conda"

add_keyword_Molecular_biology:
	job-scrapper configure keywords add -y Molecular_biology \
		"Molecular biology" "Biologie moleculaire" "ADN" "DNA" "RNA" "ARN" \
		"Protéine" "Protein" "Transcriptome" "Transcriptomique" \
		"Transcriptomic" "Protéome" "Proteome" "Métabolome" "Metabolome" \
		"Épigénome" "Epigenome" "SNP" "Indels"

add_keyword_Bioinformatic_enhanced:
	job-scrapper configure keywords add -y Bioinformatic_enhanced \
		"Bioinformatique" "Bio-informatique" "Bioinformatic" "Bio-informatic" \
		"Computational biology" "Biologie computationnelle" "HPC" "Slurm" \
		"Cluster" "Python" "Biologie numérique" "Bioinformaticien" \
		"Bio-informaticien" "Bioinformatician" "Biocomputer" "Génomique" \
		"Genomics" "Transcriptomique" "Transcriptomics" "Protéomique" \
		"Proteomics" "Métabolomique" "Metabolomics" "Systèmes biologiques" \
		"Biological systems" "Modélisation biologique" "Biological modeling" \
		"Données omiques" "Omics data" "GenBank" "UniProt" "PDB" \
		"Protein Data Bank" "Ensembl" "KEGG" \
		"Kyoto Encyclopedia of Genes and Genomes" "Reactome" "NCBI" \
		"National Center for Biotechnology Information" "GEO" \
		"Gene Expression Omnibus" "Alignement de séquences" \
		"Sequence alignment" "BLAST" "Clustal Omega" \
		"Assemblage de génome" "Genome assembly" \
		"Annotation génomique" "Genome annotation" "RNA-Seq" \
		"Single-cell RNA-Seq" "Pangénome" "Pangenome" \
		"Métagénomique" "Metagenomics" "Phylogénétique" \
		"Phylogenetics" "Docking moléculaire" "Molecular docking" \
		"Prédiction structurale des protéines" "Protein structure prediction" \
		"Réseaux de gènes" "Gene networks" "Galaxy" "PyMOL" "GROMACS" \
		"VMD" "Rosetta" "HMMER" "Smith-Waterman algorithm" \
		"Needleman-Wunsch algorithm" "Hidden Markov Models" \
		"Machine Learning" "Deep Learning" "Clustering" "PCA" \
		"Personalized medicine" "Gene therapy" "Biomarkers" \
		"Molecular evolution" "Drug discovery" "Nextflow" "Snakemake"

###################
#       DEV       #
###################
FOLDER ?= ./job_scrapper
reformat_code:
	poetry run black $(FOLDER) # Refomate code
	poetry run isort  $(FOLDER)  # Sort dependances
	poetry run mypy  $(FOLDER)  # statick typing
	poetry run pylint  $(FOLDER)  # Coding Standard


