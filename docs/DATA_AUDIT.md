# Data audit

An audit of the provided data (`data/*.csv`) and the store policy manual (`políticas_da_loja.pdf`), done before writing any code.
Every pitfall below becomes either a rule in [`PLAN.md`](PLAN.md) §4 or a test. Policy claims cite the manual's section number and quote the original Portuguese.

## 1. What the data contains

| Table | Rows | Content |
|---|---|---|
| `products` | 65 | ids 81–145, price, name, category, description, stock, status, `specs` (JSON), `created_at` |
| `categories` | 9 | Guitarras, Baixos, Baterias e Percussão, Teclados e Pianos, Violões, Instrumentos de Sopro (Madeiras), Instrumentos de Sopro (Metais), Cordas Orquestrais, Ukuleles |
| `orders` | 20 | customer, date, status, total, payment method, tracking code, ETA, notes |
| `order_items` | 22 | order, quantity, product (no unit price) |
| `customers` | 50 | name, phone, e-mail, city (all in MS) |
| `promotions` | 25 | product, % off, campaign name, `is_active` (no dates) |

- **Products per category:**
  - Violões (classical, steel-string and electro-acoustic guitars): 35
  - Ukuleles: 15
  - Guitarras: 5
  - Baixos: 4
  - Baterias e Percussão: 3
  - Teclados e Pianos: 3
  - both Sopro categories and Cordas Orquestrais: **0**
- **Product status:** 62 `active`, 2 `discontinued`, 1 `coming_soon`.
- **Order status:** 7 `delivered`, 1 `shipped`, 4 `confirmed`, 4 `pending`, 4 `cancelled` (each with a reason in `notes`).
- **Active promotions:** 4 (products 127, 121, 90 and 94).
- **Format:** all files are UTF-8 with no BOM and no malformed rows, and every `specs` JSON parses.

## 2. Pitfalls in the data

1. **Empty categories.** Woodwinds, brass and orchestral strings exist with no products. The agent must say "not available right now" instead of inventing items.
2. **Catalog size.** The manual claims "mais de 300 instrumentos" (§1); the data has 65. The data is the source of truth for what is available.
3. **Active but out of stock.** Giannini GF-3D (96) is `active` with stock 0. This is the "produto fora de estoque" case of §7.3: suggest available alternatives.
4. **Discontinued but in stock.** Ibanez Bass 2X (136) is `discontinued` with stock 13.
5. **Coming soon but already sold.** Kala KA-ABP-CTG (130) is `coming_soon` with stock 2, yet it appears in order 3 (delivered, 2 units) and order 14 (pending).
6. **Totals that don't match their items.** Order 3 is R$ 3,450 against 2 × 1,749 = R$ 3,498; order 20 is R$ 1,400 against R$ 1,488. Line items carry no unit price, so the stored total is reported and never recomputed.
7. **Past installments that break the policy.** Order 9 is 6× R$ 58.32, order 16 is 6× R$ 71.65 (minimum R$ 80) and order 18 is 12× R$ 38.33 (minimum R$ 100). The rules apply to new quotes; history is reported as stored.
8. **Duplicate, undated promotions.** Products 93, 96 and 99 have several promotions, all inactive. With no dates, `is_active` is the only signal.
9. **Promotion on a discontinued product.** An inactive Black Friday promotion points to Shelby SN-7C (113), which is discontinued with stock 0.
10. **Shared customer e-mail.** `bruno.martins@jmail.com` belongs to customers 11 and 43, so e-mail alone cannot identify a customer. Order lookup uses order id plus phone or e-mail.
11. **A stale snapshot.** Orders run from 2025-10 to 2026-03, while today is 2026-10-31.
    - Order 8 is `shipped` with an ETA of 2026-02-28, eight months late.
    - The `confirmed` orders (9–12) and the `pending` orders (13–16) date from February and March.

    Such orders are handed off to a human.
12. **No tracking yet.** `confirmed` and `pending` orders have no tracking code or ETA: they have not been dispatched.
13. **Synthetic-looking rows.** Products 135–144 have generic names ("Music Man Bass 1X Electric Bass", "Bateria Acústica Yamaha Kit 1 Studio", "Teclado Sintetizador Korg Synth 1 Pro") and implausible prices (a Korg synth at R$ 1,127, a Nord at R$ 19,567). Their `specs` JSON is formatted differently (with spaces), as if the rows were appended later. Product 145 is listed before 131.
14. **Name, description and specs contradict each other in 7 products.** Products 138, 141 and 143 in the same block are consistent.

    | id | Name | Description says | Specs say |
    |---|---|---|---|
    | 135 | Music Man Bass 1X Electric Bass | "Fender Jazz Bass com corpo em Alder" | body Ash |
    | 136 | Ibanez Bass 2X Electric Bass | "Contrabaixo Precision" (a Fender model) | — |
    | 137 | Yamaha Bass 3X Electric Bass | "Contrabaixo ativo de 5 cordas **Ibanez**" | **4** strings |
    | 139 | Bateria Acústica Yamaha Kit 1 Studio | "Bateria acústica **Pearl** Export com cascos em Poplar" | shells **Maple** |
    | 140 | Bateria Acústica Pearl Kit 2 Studio | "Bateria acústica **Tama** com cascos 100% Birch" | shells **Maple** |
    | 142 | Teclado Sintetizador Korg Synth 1 Pro | "Sintetizador workstation **Roland** com **88** teclas" | **61** keys |
    | 144 | Teclado Sintetizador Roland Synth 3 Pro | "Teclado arranjador **Yamaha**" | — |

    Questions like "tem baixo de 5 cordas?" get different answers depending on which field is read. The rule is keyed on a **detected conflict per attribute** (brand, string count, key count, wood), not on an id range. Structured fields win, and a conflicting attribute is never confirmed (PLAN §4).
15. **Promotions outside the manual's campaign ranges.**
    - The manual's campaign list is non-exhaustive (§6.1: "as principais campanhas incluem"), so extra campaign names are not a contradiction in themselves.
    - However, all 4 *active* promotions belong to campaigns the manual doesn't list ("Oferta Especial", "Desconto Exclusivo").
    - Two inactive promotions fall outside the manual's ranges: promo 1 is Black Friday at 10% (manual: 15–30%), and promo 17 is Aniversário da Loja at 30% (manual: 10–25%).

    The data's `discount_percent` is what applies.

## 3. Pitfalls in the policy manual

16. **Contradictory WhatsApp number.** §1.2 labels (67) 3341-4444 as "Telefone / WhatsApp", while §7 says "O canal de WhatsApp (67) 3321-4500 é o principal meio de atendimento remoto". The more specific section wins: §7 is the WhatsApp section, so 3321-4500 is the WhatsApp number and 3341-4444 the phone. This is the same principle as rule 18.
17. **Accented e-mail.** §1.2 has `contato@empóriodamusica.com.br`, while the cover has `contato@emporiodamusica.com.br`. The accented one is treated as a typo.
18. **Contradictory installment minimums.**
    - The §3 table says "Parcela mínima de R$ 100,00" for credit cards. §3.1 tiers it: up to 3× "sem valor mínimo de parcela (exceto abaixo de R$ 50,00)", 4–6× R$ 80, 7–12× R$ 100. The more specific §3.1 wins.
    - The R$ 50 parenthetical is read as a minimum *installment* of R$ 50 for 2–3×.
    - Combining payment methods (e.g. PIX + card) is allowed only for purchases "acima de R$ 2.000,00".
19. **Look-alike deadlines.**
    - **Withdrawal right** (§4.1, online purchases only): "7 (sete) dias corridos após o recebimento", i.e. calendar days after delivery. The refund goes to the original payment method "em até 10 dias úteis", and the store pays the return freight.
    - **Defect exchange** (§4.2): "30 (trinta) dias corridos após a compra". After that, the manufacturer's warranty applies.
    - **Preference exchange** (§4.3): "até 7 dias", with no start point stated.
    - **Legal warranty** (§8.1): 90 days "a partir da data de recebimento".
    - **Manufacturer warranty** (§8.2): 6 months to 2 years.

## 4. Rules that are easy to get wrong

20. **No stacking.** "O desconto de PIX (5%) não se aplica sobre preços já promocionais" (§6.2). Promotional prices are always shown with the original price and the % off.
21. **Scope.** The store sells instruments only. Accessories (strings, cables, picks, pedals, amplifiers, cases) are politely redirected (§1, §7.1). The manual says "Sugerir lojas parceiras quando possível" but names none, so none are invented.
22. **Shipping** (§5).
    - **Metro Campo Grande:** free for orders "acima de R$ 500,00", R$ 35 "abaixo de R$ 500,00", 1–3 business days. Exactly R$ 500.00 is undefined; we take the customer-favourable reading (free).
    - **Elsewhere:** the *cost* depends on CEP, weight and size and cannot be quoted. The delivery-time estimates are known and can be given: PAC 5–12, SEDEX 2–5 and Jadlog 3–8 business days, all tracked and insured.
    - **Large instruments** (drum kits, digital pianos, double basses) may need a special quote.
23. **Out of hours** (§2, §7.1). The agent must say when the team is back: Mon–Fri 09:00–18:00, Sat 09:00–13:00, closed Sundays and holidays. That needs the current time and a holiday calendar.
24. **The golden rule** (§7.1): "nunca fornecer informações sobre preços, estoque ou prazos sem consultar o sistema". §7.3 extends it to promotions ("verificar se ela encontra-se ativa no sistema").
25. **Complaints, data deletion and order privacy.**
    - **Complaints** (§7.3): heard with empathy, recorded and forwarded to a human, with "Prazo de retorno: 24 horas úteis".
    - **Data deletion** (§9): can be requested at any time via WhatsApp or e-mail, with no stated deadline. It goes to a human.
    - **Order privacy:** showing order data only to the order's owner is *our* rule. It is motivated by the manual's LGPD commitment (§9), not stated by it.
26. **Upcoming campaigns.** Black Friday (November) and Semana do Músico (around 11-22) are close, but no such promotion is active in the data. §7.3: "Nunca prometer um desconto que não está mais vigente."
