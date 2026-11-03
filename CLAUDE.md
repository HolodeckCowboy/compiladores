# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**v3 (T3 — análise semântica)** of the Compiladores GALS compiler. It is a copy of v2 plus semantic
actions, a symbol table, and test inputs. The parent `Compiladores/CLAUDE.md` describes v2 (language,
grammar constraints, GALS codegen bugs, `mensagens.py` layering, table layout) and still applies —
this file covers only what changed and what is currently broken.

Comments, error messages and identifiers are in Portuguese. Keep that.

## Hand-written files (new in v3)

| File | Role |
|---|---|
| `TabelaDeSimbolos.py` | Symbol table: scope stack, `inserir`/`buscar`/`marcar_usado`/`marcar_inicializado`/`finalizar`, `avisos`, `historico`, `linhas_tabela()` |
| `m2_python_v3.vgls` | **Source of truth**: full grammar with actions 1–40. `m2_python_v2.vgls` is the old, action-free grammar |
| `Semantico.py` | `execute_action` `match` over actions **1–40**; table via "pending" state (1–19), type stack (20–40) |
| `GRAMATICA_ACOES.md` | What each `#N` does and why it sits where it does |
| `testar_semantica.py` | Runs the full pipeline on a file; prints error-or-OK, warnings, symbol table |
| `teste_integracao.py` | Feeds hand-built `execute_action` sequences to `Semantico` (no parser needed) |
| `teste01..31_*.txt` | Semantic test inputs (21–31 = types); `testes_novos_13_a_20.zip` duplicates 13–20 |
| `ide.py` | After F7: error/OK + `avisos` in the message panel, symbol table in a `ttk.Treeview` |
| `resultado*.txt` | Captured outputs of earlier test runs, not inputs |

## Commands

```
python TabelaDeSimbolos.py              # 16 assert cases for the table alone
python teste_integracao.py              # 8 Semantico scenarios (7-8 = types), simulated actions
python testar_semantica.py teste05_escopo_nao_vaza_entre_funcoes.txt   # one input, real parser
for f in teste*.txt; do python testar_semantica.py "$f"; done           # all inputs
python ide.py                           # tkinter IDE, F7 compiles
```

Windows console mangles accents (`j� declarado`); set `PYTHONIOENCODING=utf-8` when reading output.
No expected-output files exist — the `teste*.txt` name states the intended outcome
(e.g. `teste02_unicidade_variavel` should error, `teste06_aviso_nao_usado` should warn).

## Semantic design

- **Scope is per function, not per block** ("Opção B"). The stack is only ever `[global]` or
  `[global, <função>]`; all locals of nested `if`/`while`/`for` blocks land in the function scope.
  Functions don't see each other's locals; inner names may shadow globals.
- **Errors** (abort, raised as `Errors.SemanticError` so the existing `except AnalysisError` catches
  them): redeclaration in the same scope, use of an undeclared name. Declare-before-use is strict,
  so a function called before its definition errors, and — unlike v2 — **a bare `x = 0;` without
  `var` is now an error** (`teste20`).
- **Warnings** (accumulate in `tabela.avisos`, never abort): declared-but-unused (emitted when a
  scope closes; action 19 → `finalizar()` closes the global scope), and used-possibly-uninitialized
  (emitted at use).
- **lvalue vs rvalue**: the grammar has `<referencia_alvo>` (actions 16/17 → `marcar_inicializado`)
  alongside `<referencia>` (14/15 → `marcar_usado`). Assignment targets and `read(...)` use the
  former, so `read(n); write(n);` warns nothing.
- Functions are inserted at action 9 with `tipo=None`, then patched by 10 (`void`) or 11 once the
  return type has been parsed. Parameters are always `inicializado=True`.
- Pending state works because SLR fires actions left-to-right and only one declarator/parameter/
  function header is in flight at a time. Action 3 is reused by declarator, parameter and return type.
- Actions receive `self.previous_token` (the last shifted token), so `token.lexeme` is the token
  right before the `#N`.
- **Type checking (20–40)** is a type stack: operands push, operators (`#25` records the operator,
  one end-of-level action per `<exp>` level) pop/push, consumers (`#4`, `#28`, `#30`, `#32`, index,
  args, write) pop. `None` = unknown type (declared without annotation), accepted anywhere; the
  first value assigned fixes it. Whole vector = `"int[]"`. Rule tables: `tipo_binario`/`tipo_unario`.
- Every end-of-binary-level action needs its **own number**: a shared `#N` is one epsilon symbol
  in SLR, its FOLLOW merges across levels and yields 17 shift/reduce conflicts.
- `Semantico()` auto-detects (`tabelas_tem_tipos`) whether `Constants.py` has actions ≥ 20 and
  disables type checking if not — otherwise `#4` would pop a type `#14` pushed for an unrelated
  expression. Simulated tests pass `Semantico(checar_tipos=True)`.

## Known stale / broken state (verify before trusting)

- `Constants.py` is generated from `m2_python_v3.vgls` (269 states) via WebGALS
  (https://lia-univali.github.io/Web-GALS/ — open the `.vgls`, "Gerar Código", it downloads a zip).
  From that zip copy **only `Constants.py`**: its `Semantico.py` is a stub and its `Lexico.py`
  needs the parent-CLAUDE.md patches again (already applied here).
- `mensagens.py` layer-1 state numbers were re-derived for 269 states by matching LR(0) kernels
  between the v2 and v3 tables; one old state can map to two new ones (before/after a `#N`),
  both get the same text. After any grammar change, re-derive again — `python mensagens.py`
  asserts catch drift.
- `exemplos.txt` compiles clean under v3 (no errors, only legit unused/uninitialized warnings).
  The `#SimulatorText` sample embedded in the `.vgls` is still the v2 one and fails semantically.

## Integração T3 (versão integrada) — leia `LEIA-ME_T3.md`
- `TabelaDeSimbolos.py` agora: aviso de "sem valor inicial" **uma vez por variável**, avisos com `(linha N)` quando `Semantico(fonte)` recebe o texto, e `linhas_tabela()`.
- `Semantico(fonte=None, checar_tipos=None, propagar_tipo=None)`: `fonte` é opcional (a IDE passa o texto do editor). Ação 41 + propagação do tipo na lista só ficam ativas se as tabelas geradas tiverem a ação 41 (ver `proxima_regeracao/`).
- Regressão automática: `python rodar_regressao.py` (32 programas em `testes/`, resultados em `testes/esperado/`). Rode depois de qualquer mudança.
- Ao regerar no WebGALS copie **só** `Constants.py` e `Sintatico.py`; `Semantico.py` e `TabelaDeSimbolos.py` são nossos.
