# Felicidade por Idade e por País

Projeto do LAB de **Inteligência Artificial / Machine Learning** da PUC-SP. O objetivo é investigar como a avaliação de vida varia com idade e características dos países usando **regressão linear, regressão logística, validação cruzada agrupada por país e visualizações**.

## Integrantes

- **Nicolas Mariano da Silva** — GitHub: `niickmds`
- **Pedro Henrique Isamu Fagunes de Souza Tsukahara Yoshissaro** — GitHub: `knutzin`

## Estrutura

```text
felicidade-idade-pais/
├── README.md
├── requirements.txt
├── lab_helpers.py
├── mylib.py
├── lab_felicidade_idade_pais.ipynb
├── data/
│   ├── cantril-ladder-age-groups.csv
│   ├── cantril-ladder-age-groups.metadata.json
│   ├── Happiness-Around-the-World-Data.csv
│   └── owid-data-readme.md
└── figures/
    ├── reta_vs_curva.png
    └── perfil_etario_demeaned.png
```

Na primeira execução, `lab_helpers.py` consulta a API pública do Banco Mundial e cria também `data/world_bank_country_table.csv` como cache.

## Como executar

Recomendado: **Python 3.11+**.

```bash
python -m venv .venv
```

No Windows:

```bash
.venv\Scripts\activate
```

No Linux/macOS:

```bash
source .venv/bin/activate
```

Depois:

```bash
pip install -r requirements.txt
jupyter notebook
```

Abra `lab_felicidade_idade_pais.ipynb` e use **Kernel → Restart & Run All**. A primeira execução precisa de internet para buscar PIB per capita PPC, população e área no Banco Mundial. Depois disso o cache local é reutilizado.

## Dados

- **Our World in Data / World Happiness Report 2024:** avaliação de vida por quatro faixas etárias (`<30`, `30–44`, `45–59`, `60+`), média de **2021–2023**. O pacote fornecido registra download em **20/09/2026**.
- **Banco Mundial / World Development Indicators:** último valor não faltante entre **2019 e 2023** de:
  - `NY.GDP.PCAP.PP.KD` — PIB per capita, PPC;
  - `SP.POP.TOTL` — população;
  - `AG.LND.TOTL.K2` — área terrestre.
- **Arquivo nacional de felicidade fornecido:** usado apenas como verificação de sanidade entre fontes; as janelas temporais não são idênticas.

A junção principal é feita por **ISO3**, nunca por nome de país.

## Principais resultados que já podem ser verificados apenas com o arquivo por idade

Nos 143 países do arquivo do OWID, cada país possui quatro linhas, uma por faixa etária. Em validação cruzada agrupada por país:

| Modelo / alvo | R² CV | RMSE CV |
| --- | ---: | ---: |
| M1 — idade → nota bruta | 0.014 | 1.243 |
| M2 — idade + idade² → nota bruta | 0.018 | 1.240 |
| M1 — idade → desvio da média do país | 0.318 | 0.276 |
| M2 — idade + idade² → desvio da média do país | 0.377 | 0.263 |

A idade sozinha explica muito pouco da **nota bruta** entre países. Quando removemos o nível médio de cada país, o formato etário fica bem mais informativo e o termo quadrático melhora o ajuste. Com os pontos médios adotados no LAB, o vértice do modelo quadrático agregado fica em aproximadamente **62.8 anos**, mais tarde do que o mínimo de 40–50 anos frequentemente citado para países de renda alta. Isso reforça a ideia central do WHR 2024: o padrão por idade varia por região, coorte e contexto.

![Reta versus curva](figures/reta_vs_curva.png)

![Perfil etário após remover a média do país](figures/perfil_etario_demeaned.png)

O notebook calcula também, após carregar o Banco Mundial, o **M3**, resíduos por país, classificação logística, AUC/acurácia em países não vistos, comparação com split aleatório, Random Forest e curvas de `P(feliz)`.

## Limitações

Os dados são **médias de grupos por país**, e não observações individuais; portanto existe risco de **falácia ecológica**. A idade é representada apenas pelo ponto médio de quatro faixas, e `60+` é uma categoria aberta representada por 70 anos. Um corte transversal também mistura efeitos de **idade** com **coorte de nascimento**. As probabilidades do classificador não devem ser interpretadas como probabilidades pessoais nem como base suficiente para decisão pública.

## Fontes

- Gallup — World Happiness Report: https://www.gallup.com/analytics/349487/world-happiness-report.aspx
- World Economic Forum — *At what age does happiness peak?*: https://www.weforum.org/stories/2015/11/at-what-age-does-happiness-peak/
- World Happiness Report 2024 — *Happiness and age*: https://www.worldhappiness.report/ed/2024/happiness-and-age-summary/
- World Happiness Report 2024 — capítulo sobre idade: https://www.worldhappiness.report/ed/2024/happiness-of-the-younger-the-older-and-those-in-between/
- Our World in Data — *Self-reported life satisfaction by age*: https://ourworldindata.org/grapher/cantril-ladder-age-groups
- World Bank — World Development Indicators: https://data.worldbank.org/
- Jonathan Rauch — *The Happiness Curve*: https://us.macmillan.com/books/9781427292988/thehappinesscurve/

## GitHub

Antes de entregar:

```bash
git init
git add .
git commit -m "Lab: felicidade por idade e pais"
git branch -M main
git remote add origin https://github.com/niickmds/felicidade-idade-pais.git
git push -u origin main
```

Para cumprir o requisito da atividade, **os dois integrantes devem aparecer em commits**. O segundo integrante (`knutzin`) deve também fazer pelo menos um commit/push no repositório.
