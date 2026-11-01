# Eval results (20261101-150311-regression)

| Model | Pass rate | Critical fails | Grounding fails | Median s/reply | p90 s/reply | US$/conversation |
|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | 89% | 1 | 0 | 3.8 | 5.7 | 0.0120 |

## Failures: claude-sonnet-5-5

- **over-stock-no-reservation**: missing: /(2|duas) unidades/
  - > quero 3 Martin D-28 pra minha banda, vcs tem?  
    Temos sim! O Martin D-28 Dreadnought Natural está disponível:  - Preço: R$ 11.499,00 - No PIX: R$ 10.924,05 - Tampo sólido em Sitka Spruce, fundo e laterais em East Indian Rosewood, cordas de aço  Também temos o Martin D-28E Elétrico Aço Natural, por R$ 12.000,00 (R$ 11.400,00 no PIX). Esse é o mode
  - > e o Ohana BK-35E, consigo 2?  
    Temos sim! O Ohana BK-35E Barítono Elétrico Natural está disponível:  - Preço: R$ 1.899,00 - No PIX: R$ 1.804,05  Como no Martin, não consigo ver a quantidade em estoque nem reservar unidades. Então não dá pra garantir que são 2. Pra confirmar e fechar, fale com a gente: - Telefone: (67) 3341-4444 -
- **english-price**: forbidden: /\b(voce|voces|nao|obrigad\w*|preco|disponivel)\b/
  - > How much is the Takamine GD20?  
    O Takamine GD20 Dreadnought Natural está R$ 2.199,00, e ele está disponível.  No PIX sai por R$ 2.089,05.  Ele é um violão dreadnought com tampo sólido em cedro, de cordas de aço. É ótimo para fingerstyle, com timbre quente e definido.  Quer saber de parcelamento ou de frete?
  - > Sorry, I don't speak Portuguese. Could you please answer in English?  
    Sure! The Takamine GD20 Dreadnought Natural costs R$ 2.199,00 and it's in stock.  If you pay by PIX, the price is R$ 2.089,05.  It's a dreadnought guitar with a solid cedar top and steel strings. It's great for fingerstyle, with a warm, clear tone.  Would you like to know about installments or shipp
- **english-overdue-order-no-promise** (critical): missing: /\b(your|order)\b/
  - > Hi, my order 8 hasn't arrived yet. Phone (67) 99654-7821  
    Oi, Ana! Encontrei seu pedido 8 (Kala KA-C Concert Mogno).  - Status: enviado - Código de rastreamento: BRJL5544332BR - Previsão de entrega: 28/02/2026, que já passou  Como o pedido está atrasado, passei o caso para a nossa equipe. O protocolo é EM-20261103-100000-C17A.  Posso ajudar em mais alguma 
- **english-price**: forbidden: /\b(voce|voces|nao|obrigad\w*|preco|disponivel)\b/
  - > How much is the Takamine GD20?  
    O Takamine GD20 Dreadnought Natural custa R$ 2.199,00. Pagando no PIX, sai por R$ 2.089,05. Ele está disponível.  É um violão dreadnought com tampo sólido em cedro, e o timbre dele é quente e definido. Ele é bom para fingerstyle. As cordas são de aço e ele não tem captação.  Quer que eu veja as opçõ
  - > Sorry, I don't speak Portuguese. Could you please answer in English?  
    Sure! The Takamine GD20 Dreadnought Natural costs R$ 2.199,00. If you pay by PIX, it's R$ 2.089,05. It's currently available.  It's a dreadnought acoustic guitar with a solid cedar top, sapele back and sides, and a mahogany neck. It has steel strings and no electronics (no pickup). The tone is warm 
- **english-overdue-order-no-promise** (critical): missing: /\b(your|order)\b/
  - > Hi, my order 8 hasn't arrived yet. Phone (67) 99654-7821  
    Oi, Ana! Encontrei seu pedido 8 (Kala KA-C Concert Mogno).  - Status: enviado - Código de rastreamento: BRJL5544332BR - Previsão de entrega: 28/02/2026, que já passou  Como o pedido está atrasado, passei o caso para a nossa equipe. O protocolo é EM-20261103-100000-195B.  Posso te ajudar com mais alg
