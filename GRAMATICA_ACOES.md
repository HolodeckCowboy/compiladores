
---

## Ação 41 — propagação do tipo na lista (OPCIONAL: só existe depois da próxima regeração)

| # | Posição | O que faz |
|---|---|---|
| 41 | logo após `var` em `<declaracao>` | Começa uma nova declaração (zera o grupo de nomes). Com ela, `var a, b, c: int;` tipa os três: o tipo **escrito** no último nome vale para os anteriores sem tipo e sem `= valor`. Tipo inferido (`var q = 5`) nunca se propaga. |

Produção: `<declaracao> ::= var #41 <lista_declaradores> semicolon;`
Projeto pronto em `proxima_regeracao/m2_python_v3_com_propagacao.vgls`. Sem a ação 41 nas tabelas a propagação fica desligada
(`tabelas_tem_propagacao()` em `Semantico.py`), então o código atual funciona igual.
