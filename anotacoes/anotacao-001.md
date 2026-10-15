
Faça uma análise completa dos arquivos da pasta 'salvos/monitoramento' e salve em html na pasta 'resultados'.

---

Você consegue colocar o arquivo 'resultados/analise_monitoramento.html' no github pages para outra pessoa visualizar?

---

Faça o seguinte. Torne este repositório público, instale o `gh` (Github CLI) e faça o que for necessário.

---

Documente tudo em 'resultados', em arquivo html sem sobrescrever outro arquivo, por exemplo, quando precisar atualizar a página, o que fazer. O passo a passo para atualizar e compartilhar informações com terceiros.

---

Pesquise na internet as fontes primárias dos dados dos arquivos da pasta 'salvos/monitoramento'. Pesquise principalmente no portal da transparência do governo de mato grosso do sul. Salve os resultados das pesquisas na pasta 'resultados', em html, sem sobrescrever nenhum arquivo.

---

Dá pra construir robôs de acompanhamento permanente e automático, tanto nos domínios do governo do Estado quanto nas APIs do Tesouro Nacional (os Estados têm que enviar mensalmente dados ao Tesouro referentes ao RGF e ao RREO - disciplinados na Lei de Responsabilidade Fiscal). Nem todos são enviados. Os que são enviados, dá pra manter comparação permanente com outros Estados. Os que não são enviados, acompanhamos nos domínios estaduais. Como há uma infinidade de dados, precisamos definir o foco.

---

Pesquise na internet nos domínios do TSE as bases de dados dos resultados das eleições brasileiras de 2026 e de 2022. Salve os resultados da pesquisa em arquivo html na pasta 'pesquisas'. Apresente as urls para os arquivos brutos (por exemplo, csv). Resultados por seção eleitoral.

---

Faça o seguinte:
1. Confirme se o arquivo 'dados/votacao_secao_2026_MS/votacao_secao_2026_MS.csv' contém os resultados das eleições 2026 para mato grosso do sul, votação por seção eleitoral, e quais cargos; se necessário, olhe o arquivo 'dados/votacao_secao_2026_MS/leiame.pdf'.
2. Baixe para a pasta 'dados/ibge-mapas-e-dados' dos domínios do IBGE (Instituto Brasileiro de Geografia e Estatística) o shapefile referente ao Estado de Mato Grosso do Sul, com as deliminatações dos municípios
3. Construa na pasta 'dados/ibge-mapas-e-dados' um arquivo csv com a correspondência de códigos de municípios do IBGE e do TSE, considerando o Estado de Mato Grosso do Sul.
4. Monte código python na pasta 'notebooks-e-python' para um dashboard em streamlit, utilizando o ambiente virtual anaconda 'llm_001', com exibição dos mapas de votação utilizando os shapefiles dos mapas do ibge (ou outro correspondente) com filtro por candidato a deputado estadual, os 50 com maiores votação, para visualizar desempenho do candidato por município.
5. Rode o servidor.

---

No dashboard, utilize o nome político (que aparece na urna),não o nome real.

---

Me passe a orientação para colocar na nuvem do streamlit, para deixar disponível para outras pessoas visualizarem por meio de uma url.

---

Quais arquivos ainda impedem o commit e push completo repositório para o github?

---

Faça todos os procedimentos necessários para o deploy na nuvem do streamlit.

---


