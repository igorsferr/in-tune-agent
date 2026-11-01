# Eval results (20261101-145601-regression)

| Model | Pass rate | Critical fails | Grounding fails | Median s/reply | p90 s/reply | US$/conversation |
|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | 0% | 0 | 0 | 3.4 | 4.5 | 0.0091 |

## Failures: claude-sonnet-5-5

- **holiday-tomorrow-closed**: missing: /fechad|nao (abrimos|abre|abriremos|vamos abrir|funciona|funcionamos)/; forbidden: /(^|[.!?]\s+)(abrimos|a gente abre|a loja abre|funcionamos)\s+(das\s+)?0?9(:00|h)[^.!?\n]{0,15}18/
  - > vcs abrem amanhã?  
    Hoje é quinta (19/11), então amanhã é sexta-feira. A gente abre das 09:00 às 18:00. 🎶  Não tenho como confirmar se amanhã tem alguma alteração de horário por feriado ou data especial. Em geral, seguimos o horário normal de sexta.  Posso ajudar em mais alguma coisa?
- **holiday-next-monday-closed**: forbidden: /(abrimos|abre|abriremos|abririamos|estamos abertos|estaremos abertos|funcionamos|funciona) (sim|normalmente)/; forbidden: /segunda[^.!?\n]{0,40}\b0?9(:00|h)[^.!?\n]{0,15}18/
  - > Vocês abrem na segunda-feira?  
    Abrimos sim! Na segunda-feira o horário é das 09:00 às 18:00.  Só um aviso: segunda, 02/11, pode ser feriado e, em feriados, a loja fica fechada. Não consigo confirmar isso por aqui. Se quiser ter certeza, é só ligar no (67) 3341-4444.  Hoje (sábado) estamos abertos até 13:00. Posso ajudar com mais 
- **holiday-tomorrow-closed**: missing: /fechad|nao (abrimos|abre|abriremos|vamos abrir|funciona|funcionamos)/; forbidden: /(amanha|sexta)[^.!?\n]{0,40}\b0?9(:00|h)[^.!?\n]{0,15}18/
  - > vcs abrem amanhã?  
    Hoje é quinta (19/11), então amanhã é sexta-feira. Pelo horário da loja, sexta a gente abre das 09:00 às 18:00. 🎶  Não tenho como confirmar se amanhã é feriado ou data especial, mas o horário normal é esse. Posso ajudar em mais alguma coisa?
- **holiday-next-monday-closed**: forbidden: /(abrimos|abre|abriremos|abririamos|estamos abertos|estaremos abertos|funcionamos|funciona) (sim|normalmente)/; forbidden: /segunda[^.!?\n]{0,40}\b0?9(:00|h)[^.!?\n]{0,15}18/
  - > Vocês abrem na segunda-feira?  
    Abrimos sim! Na segunda-feira a loja funciona das 09:00 às 18:00.  Hoje (sábado) estamos abertos até as 13:00. Se a segunda for feriado, a loja fica fechada, mas não tenho essa informação de datas especiais. Posso ajudar com mais alguma coisa?
