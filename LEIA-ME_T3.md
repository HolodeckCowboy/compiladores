# T3 — Análise Semântica: versão integrada

## Mapa da pasta
```
(raiz)               compilador: Constants, Lexico, Sintatico, Semantico, TabelaDeSimbolos, mensagens, ide, main
                     ferramentas: testar_semantica.py, rodar_regressao.py, teste_integracao.py, teste_propagacao.py
m2_python_v3.vgls    projeto ATUAL do WebGALS (fonte da verdade da gramática)
testes/              32 programas de teste + testes/esperado/ (resultado certo de cada um)
proxima_regeracao/   atualização opcional (propagação do tipo na lista) — ver abaixo
antigo/              material da versão v2 — só referência
CLAUDE.md            anotações técnicas do projeto
```

## Começar
`python rodar_regressao.py` → tem que terminar em **`32 passaram, 0 falharam`**.
Um programa só: `python testar_semantica.py testes/teste09_caso_completo_limpo.txt`.
IDE: `python ide.py` (editor + painel de mensagens + tabela de símbolos).

## O que cobre (enunciado do T3)
| Item | Peso | Estado |
|---|---|---|
| Inserir com tipo, modalidade e escopo | 2 | ✅ |
| Declaração no escopo de uso, sem vazar | 2 | ✅ |
| Unicidade no escopo | 1 | ✅ |
| Aviso de declarado e não usado | 1 | ✅ |
| Aviso de uso sem inicializar | 1 | ✅ |
| Tabela de símbolos na IDE | 1 | ✅ (`ide.py`) |
| Compatibilidade de tipos | 2 | ✅ (ações 20–40) |

## Atualização opcional: tipo na lista (`var a, b: int;`)
**Defeito atual:** `var a, b: int; a = "texto";` compila sem erro (o `a` não recebe `int`; só o último nome recebe).
**Correção pronta** (ação 41, 270 estados, 0 conflitos): `proxima_regeracao/m2_python_v3_com_propagacao.vgls`.
1. Abra esse `.vgls` no WebGALS → **Gerar Código** (Python, Léxico e Sintático).
2. Copie **só** `Constants.py` e `Sintatico.py` para a raiz.
3. Copie o conteúdo de `proxima_regeracao/testes_apos_regeracao/` para dentro de `testes/` (substitui `esperado/`).
4. `python rodar_regressao.py` → tem que dar **`36 passaram, 0 falharam`**.
5. `python mensagens.py` **vai falhar** (os números dos estados mudaram). As mensagens de erro de sintaxe precisam ser
   remapeadas: mande o `Constants.py` regerado para quem mantém o `mensagens.py`. Até lá, só o texto de alguns erros de
   **sintaxe** pode sair trocado; erros semânticos e de tipo não dependem disso.
Se não regerar, nada quebra: a propagação fica desligada sozinha.

## Decisões e limitações conhecidas
- Escopo por **função**; variável e função precisam ser declaradas **antes** do uso.
- Inicialização checada na ordem do texto (não segue o fluxo de `if`/laço).
- `ide.py` usa fonte 11/10 (o enunciado do T2 pedia 14).
- Mensagem de erro de sintaxe após `var a: int` (falta `;`) lista alternativas de parâmetro (`)`, `{`): o estado é compartilhado.
- Criar `Semantico()` sem o texto deixa os avisos com "posição N" em vez de "linha N".
