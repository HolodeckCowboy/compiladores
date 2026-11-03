"""Tabela de símbolos para o T3 — Análise Semântica.

Granularidade de escopo escolhida: por FUNÇÃO (Opção B), não por bloco.
Existem no máximo dois níveis simultâneos:
  - escopo GLOBAL: sempre existe, guarda variáveis globais e as funções.
  - escopo de FUNÇÃO: aberto ao entrar numa <subrotina>, fechado ao sair.
    Guarda parâmetros e todas as variáveis locais declaradas em qualquer
    bloco aninhado dentro da função (if, while, for, bloco solto) — todas
    caem no MESMO escopo, não um por bloco.

Esta classe é independente da gramática/WebGALS de propósito: pode (e deve)
ser testada sozinha antes de conectar a qualquer ação semântica.
"""

from dataclasses import dataclass, field
from enum import Enum, auto

from Errors import SemanticError

# Usamos a EXCEÇÃO REAL do projeto (Errors.SemanticError), não uma própria --
# assim o erro semântico é pego pelo mesmo "except AnalysisError" que já
# existe em ide.py e main.py, sem precisar mudar nada lá. ErroSemantico é só
# um apelido em português para não quebrar os testes já escritos.
ErroSemantico = SemanticError


class Modalidade(Enum):
	VARIAVEL  = auto()
	VETOR     = auto()
	PARAMETRO = auto()
	FUNCAO    = auto()


@dataclass
class Simbolo:
	nome:         str
	tipo:         str          # "int", "float", "char", "string", "bool", ou None se ainda não inferido
	modalidade:   Modalidade
	escopo:       str          # "global" ou o nome da função dona do escopo
	inicializado: bool = False
	usado:        bool = False
	avisado_init: bool = False  # ja avisou 'sem valor inicial' para este simbolo?
	posicao:      int  = -1    # posição no código-fonte onde foi declarado (para mensagens de erro)


class TabelaDeSimbolos:

	def __init__(self, fonte: str = None):
		# Texto-fonte (opcional): se informado, os avisos dizem 'linha N' em vez
		# de 'posição P'. A IDE deve passar o texto do editor.
		self.fonte = fonte

		# pilha de escopos ativos; cada escopo é {nome: Simbolo}
		self._pilha = [{}]
		self._nomes_escopo = ["global"]

		# histórico de TODOS os símbolos já vistos (inclusive de escopos já
		# fechados) — necessário para a IDE mostrar a tabela completa no final,
		# já que escopos de função são descartados da pilha ao sair deles.
		self.historico: list[Simbolo] = []

		# avisos acumulados ao longo da análise (não interrompem a compilação)
		self.avisos: list[str] = []

	def _onde(self, posicao: int) -> str:
		if posicao is None or posicao < 0:
			return ""
		if self.fonte is not None:
			return " (linha %d)" % (self.fonte.count("\n", 0, posicao) + 1)
		return " (posição %d)" % posicao

	# ------------------------------------------------------------------
	# Controle de escopo
	# ------------------------------------------------------------------

	def entrar_escopo(self, nome: str):
		"""Abre um novo escopo (chamar ao entrar numa <subrotina>)."""
		self._pilha.append({})
		self._nomes_escopo.append(nome)

	def sair_escopo(self):
		"""Fecha o escopo atual, emitindo avisos de 'declarado e não usado'
		para tudo que ficou sem uso dentro dele, e descarta o escopo da pilha
		(mas mantém os símbolos no histórico, para a visualização na IDE)."""
		escopo = self._pilha.pop()
		self._nomes_escopo.pop()

		for simbolo in escopo.values():
			if not simbolo.usado:
				self.avisos.append(
					"aviso: '%s' (%s) declarado em '%s'%s e nunca usado"
					% (simbolo.nome, simbolo.modalidade.name.lower(), simbolo.escopo,
					   self._onde(simbolo.posicao))
				)

	@property
	def escopo_atual(self) -> str:
		return self._nomes_escopo[-1]

	# ------------------------------------------------------------------
	# Inserção
	# ------------------------------------------------------------------

	def inserir(self, nome: str, tipo: str, modalidade: Modalidade,
	            inicializado: bool = False, posicao: int = -1) -> Simbolo:
		"""Insere um identificador no escopo ATUAL (topo da pilha).
		Lança ErroSemantico se o nome já existir nesse mesmo escopo
		(unicidade é por escopo, não global)."""
		escopo_topo = self._pilha[-1]

		if nome in escopo_topo:
			raise ErroSemantico(
				"identificador '%s' já declarado no escopo '%s'" % (nome, self.escopo_atual),
				posicao,
			)

		simbolo = Simbolo(
			nome=nome, tipo=tipo, modalidade=modalidade,
			escopo=self.escopo_atual, inicializado=inicializado, posicao=posicao,
		)
		escopo_topo[nome] = simbolo
		self.historico.append(simbolo)
		return simbolo

	# ------------------------------------------------------------------
	# Busca / uso
	# ------------------------------------------------------------------

	def buscar(self, nome: str, posicao: int = -1) -> Simbolo:
		"""Procura um identificador do escopo atual para fora, até o global.
		Com escopo por função (Opção B), isso nunca 'vaza' para o escopo de
		OUTRA função — só existem dois níveis possíveis na pilha a qualquer
		momento: [global] ou [global, <funcao_atual>]."""
		for escopo in reversed(self._pilha):
			if nome in escopo:
				return escopo[nome]

		raise ErroSemantico(
			"identificador '%s' não declarado no escopo atual ('%s')" % (nome, self.escopo_atual),
			posicao,
		)

	def marcar_usado(self, nome: str, posicao: int = -1) -> Simbolo:
		"""Busca o identificador, marca como usado, e avisa (sem travar)
		se ele ainda não tinha sido inicializado."""
		simbolo = self.buscar(nome, posicao)
		simbolo.usado = True

		if not simbolo.inicializado and not simbolo.avisado_init:
			simbolo.avisado_init = True   # avisa so no primeiro uso, para nao poluir
			self.avisos.append(
				"aviso: '%s' usado possivelmente sem valor inicial%s"
				% (nome, self._onde(posicao))
			)

		return simbolo

	def marcar_inicializado(self, nome: str, posicao: int = -1):
		"""Chamar sempre que o identificador recebe um valor (na declaração
		com '=', numa atribuição, ou como alvo de um read() -- read() também
		conta como "dar valor", então deve chamar este método, não
		marcar_usado, para não gerar aviso falso de 'sem valor inicial'
		logo em seguida."""
		simbolo = self.buscar(nome, posicao)
		simbolo.inicializado = True
		return simbolo

	# ------------------------------------------------------------------
	# Encerramento
	# ------------------------------------------------------------------

	def finalizar(self):
		"""Chamar ao final da análise do <programa> inteiro. O escopo global
		nunca é fechado por 'sair_escopo' durante a análise normal (não existe
		produção que 'saia' do módulo) -- esta é a única forma de gerar também
		os avisos de 'declarado e não usado' para identificadores globais."""
		while self._pilha:
			self.sair_escopo()


	# ------------------------------------------------------------------
	# Visualização (usada nos testes agora e na IDE depois)
	# ------------------------------------------------------------------

	def linhas_tabela(self) -> list:
		"""Tabela completa (inclui escopos já fechados) como linhas de texto
		alinhadas. A mesma informação servirá para o componente da IDE."""
		cab = ("NOME", "TIPO", "MODALIDADE", "ESCOPO", "USADO", "INICIALIZADO")
		linhas = [cab]
		for s in self.historico:
			linhas.append((
				s.nome, s.tipo if s.tipo else "-", s.modalidade.name.lower(),
				s.escopo, "sim" if s.usado else "nao", "sim" if s.inicializado else "nao",
			))
		larg = [max(len(l[i]) for l in linhas) for i in range(len(cab))]
		return ["  ".join(c.ljust(larg[i]) for i, c in enumerate(l)).rstrip() for l in linhas]


# ===========================================================================
# Testes — rodar com `python TabelaDeSimbolos.py`
# ===========================================================================

if __name__ == "__main__":

	# --- Caso 1: inserir e buscar no mesmo escopo (global) ---
	t = TabelaDeSimbolos()
	t.inserir("contador", "int", Modalidade.VARIAVEL)
	s = t.buscar("contador")
	assert s.nome == "contador" and s.tipo == "int"
	print("Caso 1 OK: inserir/buscar no escopo global")

	# --- Caso 2: unicidade no mesmo escopo ---
	t = TabelaDeSimbolos()
	t.inserir("x", "int", Modalidade.VARIAVEL)
	try:
		t.inserir("x", "float", Modalidade.VARIAVEL)
		assert False, "deveria ter lançado ErroSemantico"
	except ErroSemantico as e:
		assert "já declarado" in e.message
	print("Caso 2 OK: unicidade detectada")

	# --- Caso 3: mesmo nome em escopos DIFERENTES é permitido ---
	t = TabelaDeSimbolos()
	t.inserir("x", "int", Modalidade.VARIAVEL)          # x global
	t.entrar_escopo("f")
	t.inserir("x", "float", Modalidade.PARAMETRO)       # x dentro de f -- não é duplicata
	s_local = t.buscar("x")
	assert s_local.tipo == "float" and s_local.escopo == "f"
	t.sair_escopo()
	s_global = t.buscar("x")
	assert s_global.tipo == "int" and s_global.escopo == "global"
	print("Caso 3 OK: mesmo nome em escopos diferentes não conflita")

	# --- Caso 4: escopo proibido -- variável local de f não aparece fora ---
	t = TabelaDeSimbolos()
	t.entrar_escopo("f")
	t.inserir("y", "int", Modalidade.VARIAVEL)
	t.sair_escopo()
	try:
		t.buscar("y")
		assert False, "y não deveria ser visível fora de f"
	except ErroSemantico as e:
		assert "não declarado" in e.message
	print("Caso 4 OK: variável local não vaza para fora da função")

	# --- Caso 5: escopo proibido entre DUAS funções (não vê uma a outra) ---
	t = TabelaDeSimbolos()
	t.entrar_escopo("f")
	t.inserir("local_f", "int", Modalidade.VARIAVEL)
	t.sair_escopo()
	t.entrar_escopo("g")
	try:
		t.buscar("local_f")
		assert False, "g não deveria enxergar variável local de f"
	except ErroSemantico:
		pass
	t.sair_escopo()
	print("Caso 5 OK: função g não enxerga variável local de f")

	# --- Caso 6: declarado e não usado -- vira aviso ao sair do escopo ---
	t = TabelaDeSimbolos()
	t.entrar_escopo("f")
	t.inserir("nao_usado", "int", Modalidade.VARIAVEL)
	t.sair_escopo()
	assert any("nao_usado" in a and "nunca usado" in a for a in t.avisos)
	print("Caso 6 OK: aviso de declarado-e-não-usado gerado")

	# --- Caso 7: usado sem inicializar -- vira aviso no momento do uso ---
	t = TabelaDeSimbolos()
	t.inserir("sem_valor", "int", Modalidade.VARIAVEL, inicializado=False)
	t.marcar_usado("sem_valor")
	assert any("sem valor inicial" in a for a in t.avisos)
	print("Caso 7 OK: aviso de uso sem inicialização gerado")

	# --- Caso 8: inicializar DEPOIS de declarar remove o risco de aviso futuro ---
	t = TabelaDeSimbolos()
	t.inserir("v", "int", Modalidade.VARIAVEL, inicializado=False)
	t.marcar_inicializado("v")   # ex: uma atribuição "v = 5;"
	t.marcar_usado("v")
	avisos_sobre_v = [a for a in t.avisos if "sem valor inicial" in a]
	assert avisos_sobre_v == []
	print("Caso 8 OK: inicializar antes de usar não gera aviso")

	# --- Caso 9: histórico mantém símbolos mesmo após sair do escopo (p/ IDE) ---
	t = TabelaDeSimbolos()
	t.entrar_escopo("f")
	t.inserir("temp", "int", Modalidade.VARIAVEL)
	t.sair_escopo()
	assert any(s.nome == "temp" for s in t.historico)
	print("Caso 9 OK: histórico preserva símbolos de escopos já fechados")

	# --- Caso 10: VETOR -- inserir, usar indexado, sem falso aviso ---
	t = TabelaDeSimbolos()
	t.inserir("vetor", "int", Modalidade.VETOR, inicializado=True)  # ex: "var vetor[10]: int;"
	s = t.marcar_usado("vetor")  # ex: "write(vetor[0]);"
	assert s.modalidade == Modalidade.VETOR
	avisos_sem_valor = [a for a in t.avisos if "sem valor inicial" in a]
	assert avisos_sem_valor == []
	print("Caso 10 OK: vetor usado sem gerar falso aviso de não-inicializado")

	# --- Caso 11: PARAMETRO -- sempre nasce inicializado (recebe valor na chamada) ---
	t = TabelaDeSimbolos()
	t.entrar_escopo("f")
	t.inserir("p", "int", Modalidade.PARAMETRO, inicializado=True)
	t.marcar_usado("p")  # usar o parâmetro dentro do corpo da função
	t.sair_escopo()
	avisos_p = [a for a in t.avisos if "p" in a]
	assert avisos_p == []  # nem "não usado" nem "sem valor inicial"
	print("Caso 11 OK: parâmetro usado não gera aviso nenhum")

	# --- Caso 12: FUNCAO -- inserir e chamar não deve soar como 'sem valor inicial' ---
	t = TabelaDeSimbolos()
	t.inserir("soma", "int", Modalidade.FUNCAO, inicializado=True)  # funções já "prontas" ao inserir
	t.marcar_usado("soma")  # ex: uma chamada "soma(1, 2)"
	avisos_soma = [a for a in t.avisos if "soma" in a]
	assert avisos_soma == []
	print("Caso 12 OK: função chamada não gera aviso falso de inicialização")

	# --- Caso 13: duplicidade também vale para função (mesmo escopo = global) ---
	t = TabelaDeSimbolos()
	t.inserir("soma", "int", Modalidade.FUNCAO, inicializado=True)
	try:
		t.inserir("soma", "void", Modalidade.FUNCAO, inicializado=True)
		assert False, "duas funções com o mesmo nome deveriam colidir"
	except ErroSemantico as e:
		assert "já declarado" in e.message
	print("Caso 13 OK: nome de função duplicado também é barrado")

	# --- Caso 14: padrão read(x) -- marcar_inicializado evita aviso de 'sem valor' ---
	t = TabelaDeSimbolos()
	t.inserir("n", "int", Modalidade.VARIAVEL, inicializado=False)  # "var n: int;" sem valor
	t.marcar_inicializado("n")   # ex: "read(n);" -- read() entrega um valor
	t.marcar_usado("n")          # ex: "write(n);" depois do read
	avisos_n = [a for a in t.avisos if "sem valor inicial" in a]
	assert avisos_n == []
	print("Caso 14 OK: read() seguido de uso não gera aviso de não-inicializado")

	# --- Caso 15: finalizar() fecha o escopo global e avisa sobre o que sobrou ---
	t = TabelaDeSimbolos()
	t.inserir("global_nao_usado", "int", Modalidade.VARIAVEL, inicializado=True)
	t.inserir("global_usado", "int", Modalidade.VARIAVEL, inicializado=True)
	t.marcar_usado("global_usado")
	assert t.avisos == []  # nada ainda -- escopo global não fechou sozinho,
	                       # e ambos já nasceram inicializados, então marcar_usado
	                       # não deveria disparar o aviso de "sem valor inicial"
	t.finalizar()
	assert any("global_nao_usado" in a and "nunca usado" in a for a in t.avisos)
	assert not any("global_usado" in a and "nunca usado" in a for a in t.avisos)
	print("Caso 15 OK: finalizar() gera avisos pendentes do escopo global")

	# --- Caso 16: finalizar() também cobre escopo de função esquecido aberto ---
	# (não deveria acontecer em uso normal, mas a função não deve quebrar)
	t = TabelaDeSimbolos()
	t.entrar_escopo("f")
	t.inserir("esquecida", "int", Modalidade.VARIAVEL)
	t.finalizar()  # fecha f E o global, mesmo sem sair_escopo() explícito de f
	assert t._pilha == []
	assert any("esquecida" in a for a in t.avisos)
	print("Caso 16 OK: finalizar() esvazia toda a pilha, mesmo com escopo aberto")

	# --- Caso 17: aviso de 'sem valor inicial' sai UMA vez por variavel ---
	t = TabelaDeSimbolos()
	t.inserir("c", "int", Modalidade.VARIAVEL)
	for _ in range(5):
		t.marcar_usado("c")
	assert len([a for a in t.avisos if "sem valor inicial" in a]) == 1
	print("Caso 17 OK: uso repetido gera um unico aviso por variavel")

	# --- Caso 18: avisos dizem a LINHA quando o texto-fonte e informado ---
	fonte = "var a: int;\nvar b: int;\n"
	t = TabelaDeSimbolos(fonte)
	t.inserir("b", "int", Modalidade.VARIAVEL, posicao=fonte.index("b"))
	t.finalizar()
	assert any("(linha 2)" in a for a in t.avisos), t.avisos
	t2 = TabelaDeSimbolos()   # sem fonte: cai para 'posição'
	t2.inserir("z", "int", Modalidade.VARIAVEL, posicao=7)
	t2.finalizar()
	assert any("(posição 7)" in a for a in t2.avisos), t2.avisos
	print("Caso 18 OK: avisos informam linha (com fonte) ou posição (sem fonte)")

	print("\nTodos os 18 casos passaram.")
