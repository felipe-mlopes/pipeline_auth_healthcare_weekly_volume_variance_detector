# Todos os alvos usam o Python do .venv — não é preciso ativar o ambiente.
.RECIPEPREFIX := >
VENV := .venv
BIN  := $(VENV)/bin
APP := src/radar/presentation/streamlit/app.py
.PHONY: venv lock test extrair agendar dashboard dev importar limpar

venv: $(BIN)/radar
$(BIN)/radar: pyproject.toml requirements.lock
> ./setup.sh --dev
> @touch $@

lock: ## Regenera requirements.lock a partir do pyproject (após mudar dependências)
> rm -rf .lockenv && python3 -m venv .lockenv && .lockenv/bin/pip install -q .
> .lockenv/bin/pip freeze --exclude radar-emergentes > requirements.lock && rm -rf .lockenv

test: venv      
> $(BIN)/pytest -q

extrair: venv   
> $(BIN)/radar extrair

agendar: venv   
> $(BIN)/radar agendar --executar-ao-iniciar

dashboard: venv 
> $(BIN)/streamlit run $(APP)

dev: venv
> $(BIN)/streamlit run $(APP) --server.runOnSave=true --server.folderWatchList="$(CURDIR)/src"

importar: venv
> $(BIN)/radar importar-csv $(ARQUIVOS)

limpar: 
> rm -rf $(VENV) .pytest_cache src/*.egg-info