
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

Pesquise na internet o estudo citado na reportagem 'https://www.campograndenews.com.br/economia/ms-e-o-terceiro-estado-com-maior-gasto-tributario-do-pais-revela-estudo' e salve na pasta 'download'.

---

Faça uma pesquisa no TSE e me diga quais são as classificações das localizações por voto segundo o TSE? Zona? Seção?

---

Dos dados abertos do TSE, a respeito dos resultados de votação, quais são os níveis de detalhamento possíveis?

---

Pesquise se é possível fazer um mapeamento de subregiões de um município (por exemplo, Campo Grande - MS), de acordo com os mapas do IBGE (exemplo, shapefile) e com números de zonas e seções eleitorais de acordo com a codificação do IBGE. Apresente detalhes.

---

Após baixar os arquivos necessários de mapas do IBGE, e dados de correspondências de códigos IBGE-TSE, acrescente então ao dashboard de 'notebooks-e-python' duas novas abas:
1. Aba com mapa de votação no município de Campo Grande - MS dos 50 candidatos mais votados para deputado estadual em Mato Grosso do Sul.
2. Aba com explicação de metodologias de agregação e correspondência de códigos.
Mantenha somente os dados necessários ao dashboard, de forma que o tamanho seja compatível com versionamento no github e posterior deploy no streamlit cloud.

---

Sem alterar nada, sobre o dashboard streamlit de 'notebooks-e-python', verifique:
- Se dos dados de fontes do dashboard, a respeito dos locações de votação, há informação de latitude e longitude.
- Se no dashboard streamlit é possível colocar pinos em localizações específicas com links para a localização no google maps, com base na latitude e longitude.

---

Na aba de Campo Grande:
- Volte como era antes o filtro por locais de votação:
- Faça uma novo filtro para os links com o google maps, também com o resultado naquele local de votação (como está atualmente).

---

Busque dados também de 2022 para o que segue. Para o município de Campo Grande, crie um novo nível de agregação, semelhante a 'Locais de Votação', porém de acordo com o critério 'votação em 2026 - votação em 2022'.  Deve haver dois tons de cores: azul (se a diferença é positiva) e vermelho (se a diferença é negativa). Tons mais fortes de azul ou de vermelho devem indicar maiores altas ou quedas nos resultados de votação. O tamanho dos dados devem continuar compatíveis com versionamento no github e deploy no streamlit cloud.

---

Faça o commit e o push no github para o deploy no streamlit cloud.

---

Da mesma forma como fez para Campo Grande, na aba 'MS por município', divida por dois filtros:
1. O primeiro mantém como já está;
2. O segundo coloque a diferença de votação de 2026 com relação a 2022, colorindo os municípios de mato grosso do sul com tons de azul (associados a altas) e vermelho (associados a quedas); tons mais fortes de azul ou de vermelho devem estar associados a aumentos ou quedas mais acentuados de 2026 com relação a 2022.
Baixe os dados de 2022 para o Estado necessários para a nova funcionalidade do dashboard.

---

Na barra lateral da esquerda do dashboard, coloque ao final o texto, duas linhas:
'Elaboração: Pedro Nakashima'.
'Última atualização: ' <- colocar data e horário de agora.

---

Às vezes, quando clica na caixa de seleção e seleciona um outro candidato, demora para trocar, ou tem que clicar duas vezes para mudar. Você pode identificar qual é a causa?

---


