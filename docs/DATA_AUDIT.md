# Data audit

An audit of the provided data (`data/*.csv`) and the store policy manual (`políticas_da_loja.pdf`), done before writing any code.
Every pitfall below becomes either a rule in [`PLAN.md`](PLAN.md) §4 or a test.

## 1. What the data contains

| Table | Rows | Content |
|---|---|---|
| `products` | 65 | ids 81–145, price, name, category, description, stock, status, `specs` (JSON), `created_at` |
| `categories` | 9 | Guitars, Basses, Drums, Keyboards, Acoustic guitars, Woodwinds, Brass, Orchestral strings, Ukuleles |
| `orders` | 20 | customer, date, status, total, payment method, tracking code, ETA, notes |
| `order_items` | 22 | order, quantity, product (no unit price) |
| `customers` | 50 | name, phone, e-mail, city (all in MS) |
| `promotions` | 25 | product, % off, campaign name, `is_active` (no dates) |

- **Products per category:** acoustic guitars 35, ukuleles 15, guitars 5, basses 4, drums 3, keyboards 3, woodwinds / brass / orchestral strings **0**.
- **Product status:** 62 `active`, 2 `discontinued`, 1 `coming_soon`.
- **Order status:** 7 `delivered`, 1 `shipped`, 4 `confirmed`, 4 `pending`, 4 `cancelled` (each with a reason in `notes`).
- **Active promotions:** 4 (products 127, 121, 90 and 94).
- **Format:** all files are UTF-8 with no BOM and no malformed rows, and every `specs` JSON parses.

## 2. Pitfalls in the data

1. **Empty categories.** Woodwinds, brass and orchestral strings exist with no products. The agent must say "not available right now" instead of inventing items.
2. **Catalog size.** The manual claims "more than 300 instruments"; the data has 65. The data is the source of truth for what is in stock.
3. **Active but out of stock.** Giannini GF-3D (96) is `active` with stock 0. This is the "out of stock → suggest alternatives" case of policy §7.3.
4. **Discontinued but in stock.** Ibanez Bass 2X (136) is `discontinued` with stock 13.
5. **Coming soon but already sold.** Kala KA-ABP-CTG (130) is `coming_soon` with stock 2, yet it appears in order 3 (delivered, 2 units) and order 14 (pending).
6. **Totals that don't match their items.** Order 3 is R$ 3,450 against 2 × 1,749 = R$ 3,498; order 20 is R$ 1,400 against R$ 1,488. Line items carry no unit price, so the stored total is reported and never recomputed.
7. **Past installments that break the policy.** Order 9 is 6× R$ 58, order 16 is 6× R$ 72 (minimum R$ 80) and order 18 is 12× R$ 38 (minimum R$ 100). The rules apply to new quotes; history is reported as stored.
8. **Duplicate, undated promotions.** Products 93, 96 and 99 have several promotions, all inactive. With no dates, `is_active` is the only signal.
9. **Promotion on a discontinued product.** An inactive Black Friday promotion points to Shelby SN-7C (113), which is discontinued with stock 0.
10. **Shared customer e-mail.** `bruno.martins@jmail.com` belongs to customers 11 and 43, so e-mail alone cannot identify a customer. Order lookup uses order id plus phone or e-mail.
11. **A stale snapshot.** Orders run from Oct 2025 to Mar 2026, while today is 2026-10-31. Order 8 is `shipped` with an ETA of 2026-02-28, eight months late, and the `pending` orders date from March. Such orders are handed off to a human.
12. **No tracking yet.** `confirmed` and `pending` orders have no tracking code or ETA: they have not been dispatched.
13. **Synthetic-looking rows.** Products 135–144 have generic names ("Bass 1X", "Kit 1", "Synth 1") and implausible prices (a Korg synth at R$ 1,127, a Nord at R$ 19,567). Product 145 is listed before 131.
14. **Name, description and specs contradict each other (products 135–144).**

    | id | Name | Description says | Specs say |
    |---|---|---|---|
    | 135 | Music Man Bass 1X | "Fender Jazz Bass, Alder body" | body Ash |
    | 136 | Ibanez Bass 2X | "Precision" (a Fender model) | — |
    | 137 | Yamaha Bass 3X | "5-string **Ibanez**" | **4** strings |
    | 139 | Drum kit Yamaha Kit 1 | "**Pearl** Export, Poplar shells" | **Maple** shells |
    | 140 | Drum kit Pearl Kit 2 | "**Tama**, 100% Birch" | **Maple** shells |
    | 142 | Korg Synth 1 Pro | "**Roland** workstation, **88** keys" | **61** keys |
    | 144 | Roland Synth 3 Pro | "**Yamaha** arranger" | — |

    These ten rows also format their `specs` JSON differently, as if they were appended later. Questions like "do you have a 5-string bass?" get different answers depending on which field is read. Structured fields win, and conflicting attributes are never confirmed (PLAN §4).
15. **Campaigns that don't match the manual.** The data has "Promoção de Páscoa", "Liquidação de Inverno", "Oferta Especial" and "Desconto Exclusivo", none of which are in the manual's campaign list. Meanwhile "Volta às Aulas", which the manual lists, is not in the data.

## 3. Pitfalls in the policy manual

16. **Two phone numbers.** The cover and §1.2 give (67) 3341-4444; §7 gives WhatsApp (67) 3321-4500.
17. **Accented e-mail.** §1.2 has `contato@empóriodamusica.com.br`, while the cover has the unaccented address. The accented one is treated as a typo.
18. **Contradictory installment minimums.** The §3 table says "minimum installment R$ 100" for credit cards. §3.1 tiers it: up to 3× with no minimum (except below R$ 50), 4–6× with R$ 80, 7–12× with R$ 100. The more specific §3.1 wins.
19. **Look-alike deadlines.**
    - Withdrawal right: 7 days **after delivery**, online purchases only.
    - Preference exchange: 7 days, no start point stated.
    - Defect exchange: 30 days **after purchase**.
    - Legal warranty: 90 days **after delivery**.
    - Manufacturer warranty: 6 months to 2 years.

## 4. Rules that are easy to get wrong

20. **No stacking.** The 5% PIX discount never applies on top of a promotional price. Promotional prices are always shown with the original price and the % off (§6.2).
21. **Scope.** The store sells instruments only. Accessories (strings, cables, picks, pedals, amplifiers, cases) are politely redirected. The manual mentions partner stores but names none, so none are invented.
22. **Shipping.** In the Campo Grande metro area: free above R$ 500, otherwise R$ 35, 1–3 business days. Elsewhere the cost depends on the CEP and there is no table, so the agent cannot quote it.
23. **Out of hours** (§7.1). The agent must say when the team is back (Mon–Fri 9–18, Sat 9–13, closed Sundays and holidays). It needs the current time to do so.
24. **The golden rule** (§7.1). "Never give prices, stock or deadlines without checking the system."
25. **Privacy (LGPD, §9).** Order data is shown only to its owner. Data-deletion requests and complaints go to a human (24 business hours).
26. **Upcoming campaigns.** Black Friday (November) and Musician's Week (Nov 22) are close, but no such promotion is active in the data. Policy §7.3: never promise a discount that is not in force.

## 5. Hidden-instruction check

The materials were also searched for hidden instructions, such as an "if you are an AI…" line meant to catch candidates who paste the case into a chatbot. Nothing was found.

| Where | Checked | Result |
|---|---|---|
| Both PDFs | Colour, size, position and render mode of every text span; layers, annotations, scripts, embedded files, revisions | The extracted text matches the visible text. The only white text is table headers on dark fills; the zero-width characters are list-bullet artifacts from the Google Docs export. |
| E-mail | Rendered and raw HTML and plain-text parts | No hidden elements |
| CSVs and archive | Invisible or control characters, instruction-like text, archive comments | Clean |
