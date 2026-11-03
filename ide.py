"""IDE mínima para o compilador gerado pelo GALS (léxico + sintático + semântico).
Depois de compilar, o painel mostra o erro (ou sucesso) seguido dos avisos
semânticos, e a grade abaixo mostra a tabela de símbolos completa.
"""

import tkinter as tk
from tkinter import filedialog, ttk

import mensagens  # noqa: F401 - substitui as mensagens genéricas do GALS ao ser importado
from Lexico import Lexico
from Sintatico import Sintatico
from Semantico import Semantico
from Errors import AnalysisError

arquivo_atual = None


def linha_coluna(texto, pos):
	"""Converte um deslocamento em caracteres para (linha, coluna), ambos 1-based."""
	if pos < 0:
		pos = 0
	linha = texto.count("\n", 0, pos) + 1
	coluna = pos - (texto.rfind("\n", 0, pos) + 1) + 1
	return linha, coluna


def mensagem(texto):
	painel.config(state="normal")
	painel.delete("1.0", "end")
	painel.insert("1.0", texto)
	painel.config(state="disabled")


def mostrar_tabela(tabela=None):
	"""Preenche a grade com o histórico da tabela de símbolos (inclui escopos já fechados)."""
	grade.delete(*grade.get_children())
	if tabela is None:
		return
	for s in tabela.historico:
		grade.insert("", "end", values=(
			s.nome, s.tipo or "-", s.modalidade.name.lower(), s.escopo,
			"sim" if s.usado else "nao", "sim" if s.inicializado else "nao",
		))


def titulo():
	rotulo_arquivo.config(text=arquivo_atual or "<novo>")


def novo():
	global arquivo_atual
	editor.delete("1.0", "end")
	arquivo_atual = None
	mensagem("")
	mostrar_tabela()
	titulo()


def abrir():
	global arquivo_atual
	caminho = filedialog.askopenfilename(filetypes=[("Texto", "*.txt"), ("Todos", "*.*")])
	if not caminho:
		return
	with open(caminho, encoding="utf-8") as f:
		conteudo = f.read()
	editor.delete("1.0", "end")
	editor.insert("1.0", conteudo)
	arquivo_atual = caminho
	mensagem("")
	mostrar_tabela()
	titulo()


def salvar():
	global arquivo_atual
	caminho = arquivo_atual or filedialog.asksaveasfilename(
		defaultextension=".txt", filetypes=[("Texto", "*.txt"), ("Todos", "*.*")]
	)
	if not caminho:
		return
	with open(caminho, "w", encoding="utf-8") as f:
		f.write(editor.get("1.0", "end-1c"))
	arquivo_atual = caminho
	mensagem("arquivo salvo")
	titulo()


def compilar():
	fonte = editor.get("1.0", "end-1c")
	sem = Semantico(fonte)
	try:
		Sintatico().parse(Lexico(fonte), sem)
	except AnalysisError as e:
		linha, coluna = linha_coluna(fonte, e.position)
		texto = "Erro na linha %d, coluna %d: %s" % (linha, coluna, e.message)
		editor.mark_set("insert", "%d.%d" % (linha, coluna - 1))
		editor.see("insert")
		editor.focus_set()
	else:
		texto = "programa compilado com sucesso"
	if sem.tabela.avisos:
		texto += "\n\n" + "\n".join(sem.tabela.avisos)
	mensagem(texto)
	# em caso de erro a tabela mostra o que foi coletado até o ponto do erro
	mostrar_tabela(sem.tabela)


def posicao(_evento=None):
	linha, coluna = editor.index("insert").split(".")
	rotulo_pos.config(text="Linha: %s  Coluna: %d" % (linha, int(coluna) + 1))


root = tk.Tk()
root.title("Compilador - IDE")
root.geometry("900x650")

barra = tk.Frame(root)
barra.pack(fill="x", padx=4, pady=4)
for rotulo, acao in [
	("Novo (F1)", novo),
	("Abrir (F2)", abrir),
	("Salvar (F3)", salvar),
	("Copiar (F4)", lambda: editor.event_generate("<<Copy>>")),
	("Colar (F5)", lambda: editor.event_generate("<<Paste>>")),
	("Recortar (F6)", lambda: editor.event_generate("<<Cut>>")),
	("Compilar (F7)", compilar),
]:
	tk.Button(barra, text=rotulo, command=acao, width=12).pack(side="left", padx=2)

rotulo_arquivo = tk.Label(root, anchor="w")
rotulo_arquivo.pack(fill="x", padx=6)

quadro = tk.Frame(root)
quadro.pack(fill="both", expand=True, padx=6, pady=(0, 4))
rolagem = tk.Scrollbar(quadro)
rolagem.pack(side="right", fill="y")
editor = tk.Text(quadro, font=("Consolas", 11), undo=True, wrap="none", yscrollcommand=rolagem.set)
editor.pack(side="left", fill="both", expand=True)
rolagem.config(command=editor.yview)

painel = tk.Text(root, height=6, font=("Consolas", 10), state="disabled", bg="#f0f0f0")
painel.pack(fill="x", padx=6)

tk.Label(root, text="Tabela de símbolos", anchor="w").pack(fill="x", padx=6, pady=(4, 0))
quadro_tabela = tk.Frame(root)
quadro_tabela.pack(fill="x", padx=6)
colunas = ("NOME", "TIPO", "MODALIDADE", "ESCOPO", "USADO", "INICIALIZADO")
grade = ttk.Treeview(quadro_tabela, columns=colunas, show="headings", height=7)
for c in colunas:
	grade.heading(c, text=c)
	grade.column(c, width=120, anchor="w")
rolagem_tabela = tk.Scrollbar(quadro_tabela, command=grade.yview)
grade.config(yscrollcommand=rolagem_tabela.set)
rolagem_tabela.pack(side="right", fill="y")
grade.pack(side="left", fill="x", expand=True)

rotulo_pos = tk.Label(root, anchor="e")
rotulo_pos.pack(fill="x", padx=6, pady=2)

for tecla, acao in [
	("<F1>", novo), ("<F2>", abrir), ("<F3>", salvar),
	("<F4>", lambda: editor.event_generate("<<Copy>>")),
	("<F5>", lambda: editor.event_generate("<<Paste>>")),
	("<F6>", lambda: editor.event_generate("<<Cut>>")),
	("<F7>", compilar),
]:
	root.bind(tecla, lambda e, a=acao: (a(), "break")[1])

editor.bind("<KeyRelease>", posicao)
editor.bind("<ButtonRelease>", posicao)

titulo()
posicao()


if __name__ == "__main__":
	assert linha_coluna("abc", 0) == (1, 1)
	assert linha_coluna("abc", 2) == (1, 3)
	assert linha_coluna("ab\ncd", 3) == (2, 1)
	assert linha_coluna("ab\ncd\nef", 7) == (3, 2)
	assert linha_coluna("abc", -1) == (1, 1)
	root.mainloop()
