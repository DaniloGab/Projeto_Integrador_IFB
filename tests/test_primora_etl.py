"""Testes totalmente offline do ETL Primora; não chamam ViaCEP real."""
from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from primora_etl import (  # noqa: E402
    ClienteViaCEP, ResultadoCEP, extrair_csv, normalizar_bairro,
    normalizar_cep, normalizar_cnpj, normalizar_data, normalizar_email,
    normalizar_telefone, salvar_csv_e_relatorio, transformar, formatar_data_br,
)

BASE = Path(__file__).resolve().parents[1] / "02-clientes_distribuidora_vetor.csv"


@pytest.mark.parametrize("original,esperado", [
    ("Águas Claras", "Águas Claras"),
    ("Sul (Aguas Claras)", "Águas Claras"),
    ("Norte (Águas Claras)", "Águas Claras"),
    ("AGUAS CLARAS/DF", "Águas Claras"),
    ("Taguatinga - DF", "Taguatinga"),
    ("taguatinga sul", "Taguatinga"),
    ("Vte Pires", "Vicente Pires"),
    ("V. Pires", "Vicente Pires"),
    ("Guará II", "Guará"),
    ("guara - df", "Guará"),
    ("Local desconhecido", None),
    ("", None),
])
def test_normalizar_bairro(original, esperado):
    assert normalizar_bairro(original) == esperado


@pytest.mark.parametrize("original,esperado,status", [
    ("71926-750", "71926-750", "OK"),
    ("71926750", "71926-750", "OK"),
    ("00000-000", None, "AUSENTE_MARCADOR"),
    ("", None, "AUSENTE"),
    ("7192", None, "FORMATO_INVALIDO"),
    ("71926A750", None, "FORMATO_INVALIDO"),
])
def test_cep(original, esperado, status):
    assert normalizar_cep(original) == (esperado, status)


def test_cnpj_ficticio_sem_validar_digito():
    assert normalizar_cnpj("84959310341316") == ("84.959.310/3413-16", "OK")
    assert normalizar_cnpj("123456789") == (None, "CNPJ_FORMATO_INVALIDO")


def test_telefone_ddd_e_ddi():
    assert normalizar_telefone("+55 61 95386-2084") == ("(61) 95386-2084", "OK")
    assert normalizar_telefone("(61) 3491-1634") == ("(61) 3491-1634", "OK")
    assert normalizar_telefone("12345")[1] == "TELEFONE_INVALIDO"


@pytest.mark.parametrize("original,esperado", [
    ("2022-06-21", "2022-06-21"),
    ("28/02/2022", "2022-02-28"),
    ("08-01-2022", "2022-01-08"),
    ("Dec 24, 2023", "2023-12-24"),
    ("jul 21, 2022", "2022-07-21"),
    ("nov 19, 2021", "2021-11-19"),
])
def test_datas(original, esperado):
    assert normalizar_data(original) == (esperado, "OK")


def test_data_brasileira_com_iso_preservado_para_banco():
    assert formatar_data_br("2022-06-21") == "21/06/2022"
    assert formatar_data_br("2023-10-07") == "07/10/2023"
    assert formatar_data_br(None) is None
    clientes, *_ = transformar(extrair_csv(BASE))
    c = clientes.loc[clientes.id_cliente == "CLI0001"].iloc[0]
    assert c["data_cadastro_normalizado"] == "21/06/2022"
    assert c["data_cadastro_iso"] == "2022-06-21"


def test_data_invalida_sem_inventar():
    assert normalizar_data("31/02/2023") == (None, "DATA_INVALIDA")


def test_email_conservador():
    assert normalizar_email(" Contato@EMPRESA.com.br ") == ("contato@empresa.com.br", "OK")
    assert normalizar_email("aaa@@example.con") == (None, "EMAIL_INVALIDO")
    assert normalizar_email("contato@comercialsão.com.br")[1] == "OK"


def test_extrair_47_registros():
    d = extrair_csv(BASE)
    assert len(d) == 47
    assert d.loc[0, "cep"] == "71926-750"


def test_csv_exigencias_e_ids_duplicados(tmp_path):
    arquivo_incompleto = tmp_path / "incompleto.csv"
    arquivo_incompleto.write_text("id_cliente;cep\nCLI0001;71926-750\n", encoding="utf-8")
    with pytest.raises(ValueError, match="colunas obrigatórias"):
        extrair_csv(arquivo_incompleto)
    dados = extrair_csv(BASE)
    dados.loc[1, "id_cliente"] = dados.loc[0, "id_cliente"]
    duplicado = tmp_path / "duplicado.csv"
    dados.to_csv(duplicado, sep=";", index=False)
    with pytest.raises(ValueError, match="repetido"):
        extrair_csv(duplicado)


def test_estrutura_do_etl_sem_api():
    clientes, vendedores, aud, pend, resumo = transformar(extrair_csv(BASE), execucao_id="teste-1")
    assert len(clientes) == 47
    assert len(vendedores) == 5
    assert len(aud) >= 47
    assert len(pend) >= 1
    assert resumo["clientes_lidos"] == 47
    assert clientes["bairro_normalizado"].value_counts().to_dict() == {
        "Águas Claras": 22, "Taguatinga": 10, "Vicente Pires": 8, "Guará": 6
    }
    sem_endereco = clientes.loc[clientes["id_cliente"] == "CLI0047"].iloc[0]
    assert sem_endereco["bairro_normalizado"] is None
    assert sem_endereco["pendencia_revisao"]
    assert set(aud.columns) >= {
        "valor_original", "valor_tratado", "criterio", "fonte", "status"
    }


def test_api_simulada_sinaliza_conflito_sem_trocar_bairro():
    chamadas = []

    def via_cep_falso(cep):
        chamadas.append(cep)
        return ResultadoCEP("Taguatinga", "OK", "ViaCEP simulado")

    clientes, _, auditoria, _, resumo = transformar(extrair_csv(BASE), via_cep_falso)
    cliente = clientes.loc[clientes["id_cliente"] == "CLI0002"].iloc[0]
    assert cliente["bairro_normalizado"] == "Águas Claras"
    assert "CONFLITO_CEP_BAIRRO" in cliente["motivos_pendencia"]
    assert resumo["ocorrencias"]["CONFLITO_CEP_BAIRRO"] > 0
    assert (auditoria["status"] == "CONFLITO").any()
    assert len(chamadas) == len(set(chamadas))


def test_api_nao_preenche_bairro_ausente_automaticamente():
    d = extrair_csv(BASE)
    d.loc[d["id_cliente"] == "CLI0047", "cep"] = "72140-010"
    consulta = lambda cep: ResultadoCEP("Taguatinga", "OK")
    clientes, _, _, _, _ = transformar(d, consulta)
    cliente = clientes.loc[clientes["id_cliente"] == "CLI0047"].iloc[0]
    assert cliente["bairro_normalizado"] is None
    assert cliente["bairro_via_cep"] == "Taguatinga"
    assert cliente["status_consistencia"] == "NAO_AVALIAVEL"


def test_sem_api_externa_por_padrao():
    clientes, _, _, _, resumo = transformar(extrair_csv(BASE), consulta_cep=None)
    assert (clientes.loc[clientes["cep_normalizado"].notna(), "status_cep_api"] == "NAO_CONSULTADO").all()
    assert resumo["ocorrencias"]["CEP_NAO_CONSULTADO"] == 31


class RespostaFake:
    def __init__(self, dados):
        self.dados = dados

    def raise_for_status(self):
        return None

    def json(self):
        return self.dados


class SessionFake:
    def __init__(self):
        self.chamadas = 0

    def get(self, url, timeout):
        self.chamadas += 1
        return RespostaFake({"bairro": "Taguatinga"})


def test_cache_persistente_mockado(tmp_path):
    session = SessionFake()
    arq_cache = tmp_path / "via_cep.json"
    c = ClienteViaCEP(arq_cache, session=session)
    assert c.consultar("72140010").bairro == "Taguatinga"
    c.salvar_cache()
    c2 = ClienteViaCEP(arq_cache, session=session)
    assert c2.consultar("72140010").bairro == "Taguatinga"
    assert session.chamadas == 1
    assert c2.consultar("72140010").fonte == "ViaCEP (cache)"


def test_exportacao_arquivos(tmp_path):
    resultado = transformar(extrair_csv(BASE), execucao_id="teste-1")
    salvar_csv_e_relatorio(*resultado, pasta=tmp_path)
    assert (tmp_path / "clientes_tratados.csv").is_file()
    assert (tmp_path / "auditoria_etl.csv").is_file()
    assert (tmp_path / "resumo_etl.json").is_file()
    reaberto = pd.read_csv(tmp_path / "clientes_tratados.csv", sep=";", dtype=str)
    assert len(reaberto) == 47
    assert reaberto.loc[0, "data_cadastro_normalizado"] == "21/06/2022"
    assert reaberto.loc[0, "data_cadastro_iso"] == "2022-06-21"


def test_email_duplicado_na_base_nao_e_desprezado():
    clientes, _, auditoria, _, resumo = transformar(extrair_csv(BASE))
    assert clientes["email_compartilhado"].sum() == 4
    assert resumo["ocorrencias"]["EMAIL_COMPARTILHADO"] == 4
    assert (auditoria["status"] == "INFORMATIVO").sum() == 4


def test_api_de_outra_uf_nao_deve_definir_bairro():
    d = extrair_csv(BASE)
    d.loc[d["id_cliente"] == "CLI0047", "cep"] = "72140010"
    consulta = lambda cep: ResultadoCEP("Taguatinga", "OK", "ViaCEP simulado", "GO")
    clientes, _, _, _, resumo = transformar(d, consulta)
    cliente = clientes.loc[clientes["id_cliente"] == "CLI0047"].iloc[0]
    assert cliente["bairro_normalizado"] is None
    assert "CONFLITO_CEP_UF" in cliente["motivos_pendencia"]
    assert resumo["ocorrencias"]["CONFLITO_CEP_UF"] > 0


# Novo conjunto de testes: políticas de CEP e procedência auditável.

def test_consulta_cep_recebe_oito_digitos_sem_hifen():
    chamadas = []
    def simulado(cep):
        chamadas.append(cep)
        return ResultadoCEP("Águas Claras", "OK", "ViaCEP simulado", "DF")
    clientes, *_ = transformar(extrair_csv(BASE), simulado)
    assert chamadas
    assert all(len(v) == 8 and v.isdigit() for v in chamadas)
    assert clientes.loc[0,"cep_normalizado"] == "71926-750"
    assert clientes.loc[0,"cep_origem"] == "CADASTRO"
    assert bool(clientes.loc[0,"cep_confirmado_via_cep"])


def test_cep_valido_mas_nao_consultado_eh_rotulado_nao_verificado():
    clientes, *_ = transformar(extrair_csv(BASE))
    c = clientes.iloc[0]
    assert c["cep_normalizado"] == "71926-750"
    assert c["cep_origem"] == "CADASTRO"
    assert not bool(c["cep_confirmado_via_cep"])



@pytest.mark.parametrize("cep,esperado", [
    ("71926750", "71926-750"),
    ("71926-750", "71926-750"),
    ("71926.750", "71926-750"),
    (" 71926-750 ", "71926-750"),
    ("00000-000", None),
    ("", None),
    ("7192", None),
    ("71926A750", None),
])
def test_cep_exibicao_br_e_rejeicao(cep, esperado):
    assert normalizar_cep(cep)[0] == esperado


def test_cep_nao_localizado_preserva_codigo_mas_sinaliza():
    dados = extrair_csv(BASE).iloc[:1].copy()
    consulta = lambda cep: ResultadoCEP(None, "NAO_ENCONTRADO", "ViaCEP simulado")
    clientes, _, aud, pend, _ = transformar(dados, consulta)
    c = clientes.iloc[0]
    assert c["cep_normalizado"] == "71926-750"
    assert c["status_cep"] == "NAO_LOCALIZADO"
    assert c["status_consistencia"] == "NAO_AVALIAVEL"
    assert not c["cep_confirmado_via_cep"]
    assert c["pendencia_revisao"]
    assert "CEP_NAO_LOCALIZADO" in c["motivos_pendencia"]
    assert (aud.status == "NAO_LOCALIZADO").any()
    assert (pend.status_cep == "NAO_LOCALIZADO").any()


def test_cep_localizado_mas_divergencia_de_bairro_nao_sobrescreve():
    dados = extrair_csv(BASE).iloc[:1].copy()
    consulta = lambda cep: ResultadoCEP("Taguatinga", "OK", "ViaCEP simulado", "DF")
    clientes, *_ = transformar(dados, consulta)
    c = clientes.iloc[0]
    assert c["bairro_normalizado"] == "Águas Claras"
    assert c["bairro_via_cep"] == "Taguatinga"
    assert c["cep_normalizado"] == "71926-750"
    assert c["status_cep"] == "LOCALIZADO"
    assert c["status_consistencia"] == "DIVERGENTE_BAIRRO"
    assert c["cep_confirmado_via_cep"]
    assert c["pendencia_revisao"]


def test_bairro_equivalente_nao_e_conflito():
    dados = extrair_csv(BASE).iloc[:1].copy()
    consulta = lambda cep: ResultadoCEP("Aguas Claras", "OK", "ViaCEP simulado", "DF")
    clientes, *_ = transformar(dados, consulta)
    c = clientes.iloc[0]
    assert c["status_consistencia"] == "COMPATIVEL"
    assert not c["pendencia_revisao"]


def test_bairro_api_vazio_nao_prova_divergencia():
    dados = extrair_csv(BASE).iloc[:1].copy()
    consulta = lambda cep: ResultadoCEP(None, "OK", "ViaCEP simulado", "DF")
    clientes, *_ = transformar(dados, consulta)
    c = clientes.iloc[0]
    assert c["status_consistencia"] == "NAO_AVALIAVEL"
    assert "CONFLITO_CEP_BAIRRO" not in c["motivos_pendencia"]


def test_api_uf_divergente_preserva_cep_e_bairro():
    dados = extrair_csv(BASE).iloc[:1].copy()
    consulta = lambda cep: ResultadoCEP("Taguatinga", "OK", "ViaCEP simulado", "GO")
    clientes, *_ = transformar(dados, consulta)
    c = clientes.iloc[0]
    assert c["bairro_normalizado"] == "Águas Claras"
    assert c["cep_normalizado"] == "71926-750"
    assert c["status_consistencia"] == "DIVERGENTE_UF"
    assert c["pendencia_revisao"]


def test_api_inacessivel_nao_prova_cep_inexistente():
    dados = extrair_csv(BASE).iloc[:1].copy()
    consulta = lambda cep: ResultadoCEP(None, "INDISPONIVEL", "Falha simulada")
    clientes, *_ = transformar(dados, consulta)
    c = clientes.iloc[0]
    assert c["cep_normalizado"] == "71926-750"
    assert c["status_cep"] == "API_INDISPONIVEL"
    assert c["pendencia_revisao"]


def test_sem_cep_sem_bairro_nao_vira_plano_piloto():
    clientes, *_ = transformar(extrair_csv(BASE))
    c = clientes.loc[clientes.id_cliente == "CLI0047"].iloc[0]
    assert c["bairro_normalizado"] is None
    assert c["cep_normalizado"] is None
    assert c["status_cep"] == "AUSENTE"


def test_cep_zerado_nunca_consulta_api():
    dados = extrair_csv(BASE).iloc[:1].copy()
    dados.loc[:, "cep"] = "00000-000"
    chamadas = []
    def consulta(cep):
        chamadas.append(cep)
        return ResultadoCEP("Taguatinga", "OK")
    clientes, *_ = transformar(dados, consulta)
    assert not chamadas
    assert clientes.iloc[0]["cep_normalizado"] is None
    assert clientes.iloc[0]["status_cep"] == "AUSENTE_MARCADOR"


def test_cep_malformatado_nao_consulta_api():
    dados = extrair_csv(BASE).iloc[:1].copy()
    dados.loc[:, "cep"] = "71926X750"
    chamados = []
    def consulta(cep):
        chamados.append(cep)
        return ResultadoCEP("Taguatinga", "OK")
    clientes, *_ = transformar(dados, consulta)
    assert not chamados
    assert clientes.iloc[0]["cep_normalizado"] is None
    assert clientes.iloc[0]["status_cep"] == "FORMATO_INVALIDO"


def test_cliente_viacep_nao_cacheia_falha_de_rede(tmp_path):
    class SessaoComFalha:
        def get(self, url, timeout):
            raise ConnectionError("Sem conexão")
    api = ClienteViaCEP(tmp_path / "cache.json", session=SessaoComFalha())
    assert api.consultar("71926750").status == "INDISPONIVEL"
    assert api.cache == {}


def test_cliente_viacep_cacheia_nao_encontrado(tmp_path):
    api = ClienteViaCEP(tmp_path / "cache.json", session=type("Sessao", (), {
        "get": lambda self, url, timeout: RespostaFake({"erro": True})
    })())
    assert api.consultar("71999999").status == "NAO_ENCONTRADO"
    api.salvar_cache()
    assert "71999999" in api.cache


def test_data_br_nao_vira_texto_no_banco():
    clientes, *_ = transformar(extrair_csv(BASE))
    assert clientes.loc[0, "data_cadastro_normalizado"] == "21/06/2022"
    assert clientes.loc[0, "data_cadastro_iso"] == "2022-06-21"


# Regressões baseadas nas sete linhas problemáticas identificadas na execução real.

def test_areal_nao_e_sinonimo_automatico_de_aguas_claras():
    assert normalizar_bairro("Areal") is None
    dados = extrair_csv(BASE)
    dados = dados.loc[dados.id_cliente.isin(("CLI0010", "CLI0012", "CLI0032"))].copy()
    clientes, _, auditoria, pendencias, resumo = transformar(
        dados, lambda cep: ResultadoCEP("Areal", "OK", "ViaCEP simulado", "DF")
    )
    assert len(clientes) == 3
    assert set(clientes.bairro_normalizado) == {"Águas Claras"}
    assert set(clientes.bairro_via_cep) == {"Areal"}
    assert set(clientes.status_cep) == {"LOCALIZADO"}
    assert set(clientes.status_consistencia) == {"NAO_AVALIAVEL"}
    assert clientes.pendencia_revisao.all()
    assert all("BAIRRO_API_NAO_MAPEADO" in s for s in clientes.motivos_pendencia)
    assert len(pendencias) == 3
    assert resumo["ocorrencias"]["BAIRRO_API_NAO_MAPEADO"] == 3
    assert (auditoria.status == "NAO_AVALIAVEL").any()


def test_cli0002_continua_com_conflito_sem_sobrescrever_cadastro():
    dados = extrair_csv(BASE)
    dados = dados.loc[dados.id_cliente.eq("CLI0002")].copy()
    clientes, _, _, pendencias, _ = transformar(
        dados, lambda cep: ResultadoCEP("Taguatinga Norte", "OK", "ViaCEP simulado", "DF")
    )
    c = clientes.iloc[0]
    assert c["bairro_normalizado"] == "Águas Claras"
    assert c["bairro_via_cep"] == "Taguatinga Norte"
    assert c["status_consistencia"] == "DIVERGENTE_BAIRRO"
    assert "CONFLITO_CEP_BAIRRO" in c["motivos_pendencia"]
    assert len(pendencias) == 1


def test_falhas_de_api_compartilham_uma_consulta_por_cep_nao_por_cliente():
    dados = extrair_csv(BASE)
    dados = dados.loc[dados.id_cliente.isin(("CLI0017", "CLI0029", "CLI0033"))].copy()
    chamadas = []
    def consulta(cep):
        chamadas.append(cep)
        return ResultadoCEP(None, "INDISPONIVEL", "ViaCEP (ReadTimeout)")
    clientes, _, _, pendencias, _ = transformar(dados, consulta)
    assert set(chamadas) == {"72110800", "71900000"}
    assert len(chamadas) == 2
    assert len(clientes) == len(pendencias) == 3
    assert set(clientes.status_cep) == {"API_INDISPONIVEL"}
    assert clientes.cep_normalizado.notna().all()


def test_cliente_viacep_contem_retry_para_429_e_erros_servidor(tmp_path):
    api = ClienteViaCEP(tmp_path / "cache.json")
    retry = api.session.get_adapter("https://").max_retries
    assert retry.total == 2
    assert {429, 500, 502, 503, 504}.issubset(set(retry.status_forcelist))


def test_falha_http_reporta_codigo_na_auditoria(tmp_path):
    import requests
    class SessaoFalha:
        def get(self, url, timeout):
            resp = requests.Response()
            resp.status_code = 503
            raise requests.HTTPError("serviço fora", response=resp)
    api = ClienteViaCEP(tmp_path / "cache.json", session=SessaoFalha())
    resposta = api.consultar("72110800")
    assert resposta.status == "INDISPONIVEL"
    assert "HTTP 503" in resposta.fonte
    assert api.cache == {}



@pytest.mark.parametrize("valor_erro", [True, "true", "TRUE", " true "])
def test_viacep_erro_true_booleano_ou_texto_e_cep_nao_localizado(tmp_path, valor_erro):
    # Regressão: ViaCEP real respondeu HTTP 200 com {"erro": "true"}.
    class Sessao:
        chamadas = 0

        def get(self, url, timeout):
            self.chamadas += 1
            return RespostaFake({"erro": valor_erro})

    sessao = Sessao()
    caminho_cache = tmp_path / "cache.json"
    api = ClienteViaCEP(caminho_cache, session=sessao)
    res = api.consultar("72110800")
    assert res.status == "NAO_ENCONTRADO"
    assert res.bairro is None
    assert api.cache["72110800"]["status"] == "NAO_ENCONTRADO"
    api.salvar_cache()
    api2 = ClienteViaCEP(caminho_cache, session=sessao)
    assert api2.consultar("72110800").status == "NAO_ENCONTRADO"
    assert sessao.chamadas == 1


def test_ceps_reais_erro_true_preservados_e_pendentes(tmp_path):
    dados = extrair_csv(BASE)
    dados = dados.loc[dados.id_cliente.isin(("CLI0017", "CLI0029", "CLI0033"))].copy()

    class Sessao:
        def __init__(self):
            self.chamadas = 0

        def get(self, url, timeout):
            self.chamadas += 1
            return RespostaFake({"erro": "true"})

    sessao = Sessao()
    api = ClienteViaCEP(tmp_path / "cache.json", session=sessao)
    clientes, _, auditoria, pendencias, resumo = transformar(dados, api.consultar)
    assert len(clientes) == 3
    assert sessao.chamadas == 2  # Dois CEPs únicos para três clientes.
    assert set(clientes.status_cep) == {"NAO_LOCALIZADO"}
    assert set(clientes.status_cep_api) == {"NAO_ENCONTRADO"}
    assert set(clientes.cep_normalizado) == {"72110-800", "71900-000"}
    assert all("CEP_NAO_LOCALIZADO" in p for p in clientes.motivos_pendencia)
    assert len(pendencias) == 3
    assert resumo["ocorrencias"]["CEP_NAO_LOCALIZADO"] == 3
    assert (auditoria.status == "NAO_LOCALIZADO").sum() == 3


def test_auditoria_conflito_preserva_resultado_da_api_em_ambos_valores():
    """Regressão do CLI0002: comparar NÃO significa substituir Taguatinga Norte."""
    dados = extrair_csv(BASE)
    dados = dados.loc[dados.id_cliente.eq("CLI0002")].copy()
    clientes, _, auditoria, pendencias, _ = transformar(
        dados, lambda cep: ResultadoCEP("Taguatinga Norte", "OK", "ViaCEP simulado", "DF")
    )
    c = clientes.iloc[0]
    assert c["bairro_normalizado"] == "Águas Claras"
    assert c["bairro_via_cep"] == "Taguatinga Norte"
    evento = auditoria.loc[
        (auditoria.id_cliente == "CLI0002") &
        (auditoria.campo == "bairro_via_cep") &
        (auditoria.status == "CONFLITO")
    ].iloc[0]
    assert evento["valor_original"] == "Taguatinga Norte"
    assert evento["valor_tratado"] == "Taguatinga Norte"
    assert "Águas Claras" in evento["criterio"]
    assert "preservar" in evento["criterio"].lower()
    assert len(pendencias) == 1


def test_auditoria_bairro_original_foi_normalizado_separadamente():
    dados = extrair_csv(BASE)
    dados = dados.loc[dados.id_cliente.eq("CLI0002")].copy()
    _, _, auditoria, _, _ = transformar(
        dados, lambda cep: ResultadoCEP("Taguatinga Norte", "OK", "ViaCEP simulado", "DF")
    )
    normalizacao = auditoria.loc[
        (auditoria.id_cliente == "CLI0002") &
        (auditoria.campo == "bairro_informado")
    ].iloc[0]
    assert normalizacao["valor_original"] == "Sul (Aguas Claras)"
    assert normalizacao["valor_tratado"] == "Águas Claras"
    assert normalizacao["status"] == "NORMALIZADO"


def test_auditoria_comparacao_compatibilidade_nao_muda_bairro_viacep():
    dados = extrair_csv(BASE)
    dados = dados.loc[dados.id_cliente.eq("CLI0001")].copy()
    _, _, auditoria, _, _ = transformar(
        dados, lambda cep: ResultadoCEP("Sul (Águas Claras)", "OK", "ViaCEP simulado", "DF")
    )
    evento = auditoria.loc[
        (auditoria.id_cliente == "CLI0001") &
        (auditoria.campo == "bairro_via_cep")
    ].iloc[0]
    assert evento["status"] == "COMPATIVEL"
    assert evento["valor_original"] == "Sul (Águas Claras)"
    assert evento["valor_tratado"] == "Sul (Águas Claras)"
