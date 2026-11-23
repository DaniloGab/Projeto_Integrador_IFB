#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ETL Primora: CSV -> dados normalizados + auditoria + pendências.

O ViaCEP apenas *valida* um CEP informado. O ETL NÃO inventa CEPs a
partir de bairros, não atribui Plano Piloto a bairro ausente e não usa
CEPs de agências dos Correios como substitutos do endereço do cliente.

Exemplos:
    python primora_etl.py --saida resultados
    python primora_etl.py --saida resultados --consultar-cep

Para gravar no SQLite ou no PostgreSQL gerenciado pelo Django:
    python manage.py importar_etl --persistir --consultar-cep
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re
import tempfile
import unicodedata
from typing import Callable
from uuid import uuid4

import pandas as pd

COLUNAS_OBRIGATORIAS = (
    "id_cliente", "razao_social", "cnpj", "telefone", "email",
    "bairro_informado", "cep", "cidade", "uf", "data_cadastro",
    "vendedor_responsavel",
)

# Canonização voltada a relatórios; não significa igualdade de logradouros.
PADROES_BAIRROS = (
    (re.compile(r"^(?:(?:norte|sul) )?aguas claras(?: (?:norte|sul))?$"), "Águas Claras"),
    (re.compile(r"^taguatinga(?: (?:norte|sul|centro))?$"), "Taguatinga"),
    (re.compile(r"^(?:vicente pires|v pires|vte pires|setor habitacional vicente pires)$"), "Vicente Pires"),
    (re.compile(r"^guara(?: (?:i|ii|1|2))?$"), "Guará"),
    (re.compile(r"^plano piloto$"), "Plano Piloto"),
)

MESES = {
    "jan": 1, "january": 1, "janeiro": 1,
    "feb": 2, "february": 2, "fev": 2, "fevereiro": 2,
    "mar": 3, "march": 3, "marco": 3,
    "apr": 4, "april": 4, "abr": 4, "abril": 4,
    "may": 5, "mai": 5, "maio": 5,
    "jun": 6, "june": 6, "junho": 6,
    "jul": 7, "july": 7, "julho": 7,
    "aug": 8, "august": 8, "ago": 8, "agosto": 8,
    "sep": 9, "sept": 9, "september": 9, "set": 9, "setembro": 9,
    "oct": 10, "october": 10, "out": 10, "outubro": 10,
    "nov": 11, "november": 11, "novembro": 11,
    "dec": 12, "december": 12, "dez": 12, "dezembro": 12,
}

@dataclass(frozen=True)
class ResultadoCEP:
    bairro: str | None
    status: str  # OK, NAO_ENCONTRADO, INDISPONIVEL, NAO_CONSULTADO
    fonte: str = "ViaCEP"
    uf: str | None = None


def limpo(valor: object) -> str:
    """Texto sem espaços nas pontas e sem transformar nulo em 'nan'."""
    if valor is None or pd.isna(valor):
        return ""
    return str(valor).strip()


def chave_texto(valor: object) -> str:
    txt = unicodedata.normalize("NFKD", limpo(valor).casefold())
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", txt)).strip()


def normalizar_bairro(valor: object) -> str | None:
    chave = re.sub(r"(?: df)$", "", chave_texto(valor)).strip()
    if not chave:
        return None
    for padrao, canonico in PADROES_BAIRROS:
        if padrao.fullmatch(chave):
            return canonico
    return None  # Nada de chute por aproximação textual.


def normalizar_cep(valor: object) -> tuple[str | None, str]:
    """Só confere a sintaxe; não comprova existência do CEP."""
    original = limpo(valor)
    if not original:
        return None, "AUSENTE"
    if not re.fullmatch(r"[0-9.\-\s]+", original):
        return None, "FORMATO_INVALIDO"
    numeros = re.sub(r"\D", "", original)
    if numeros == "00000000":
        return None, "AUSENTE_MARCADOR"
    if len(numeros) != 8:
        return None, "FORMATO_INVALIDO"
    return f"{numeros[:5]}-{numeros[5:]}", "OK"


def normalizar_cnpj(valor: object) -> tuple[str | None, str]:
    numeros = re.sub(r"\D", "", limpo(valor))
    if len(numeros) != 14:
        return None, "CNPJ_FORMATO_INVALIDO"
    # Dados deliberadamente fictícios: não validar dígitos verificadores.
    return f"{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}/{numeros[8:12]}-{numeros[12:]}", "OK"


def normalizar_telefone(valor: object) -> tuple[str | None, str]:
    numeros = re.sub(r"\D", "", limpo(valor))
    if numeros.startswith("55") and len(numeros) in (12, 13):
        numeros = numeros[2:]
    if len(numeros) == 10:
        return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}", "OK"
    if len(numeros) == 11:
        return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}", "OK"
    return None, "TELEFONE_AUSENTE" if not numeros else "TELEFONE_INVALIDO"


def normalizar_email(valor: object) -> tuple[str | None, str]:
    email = limpo(valor).casefold()
    if not email:
        return None, "EMAIL_AUSENTE"
    if email.count("@") != 1 or " " in email or ".." in email:
        return None, "EMAIL_INVALIDO"
    usuario, dominio = email.split("@")
    if not usuario or not dominio or "." not in dominio or dominio.startswith(".") or dominio.endswith("."):
        return None, "EMAIL_INVALIDO"
    return email, "OK"


def normalizar_data(valor: object) -> tuple[str | None, str]:
    """Retorna ISO para persistência segura em DATE; formatação BR em campo separado."""
    texto = limpo(valor)
    if not texto:
        return None, "DATA_AUSENTE"
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", texto):
            return date.fromisoformat(texto).isoformat(), "OK"
        if re.fullmatch(r"\d{1,2}[/\-]\d{1,2}[/\-]\d{4}", texto):
            dia, mes, ano = map(int, re.split(r"[/\-]", texto))
            return date(ano, mes, dia).isoformat(), "OK"
        m = re.fullmatch(r"([A-Za-zÀ-ÿ]+)\s+(\d{1,2}),?\s*(\d{4})", texto)
        if m:
            nome_mes, dia, ano = m.groups()
            mes = MESES.get(chave_texto(nome_mes))
            if mes:
                return date(int(ano), mes, int(dia)).isoformat(), "OK"
    except ValueError:
        pass
    return None, "DATA_INVALIDA"


def formatar_data_br(data_iso: str | None) -> str | None:
    return date.fromisoformat(data_iso).strftime("%d/%m/%Y") if data_iso else None


class ClienteViaCEP:
    """ViaCEP com cache persistente de respostas conclusivas e consulta injetável nos testes."""
    def __init__(self, caminho_cache: Path, session=None):
        self.caminho_cache = Path(caminho_cache)
        self.cache = (json.loads(self.caminho_cache.read_text(encoding="utf-8"))
                      if self.caminho_cache.exists() else {})
        if session is None:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry

            session = requests.Session()
            # Só em consultas reais: até 2 novas tentativas para falhas
            # transitórias. Nos testes, a sessão simulada não é alterada.
            politica = Retry(
                total=2,
                connect=2,
                read=2,
                status=2,
                backoff_factor=0.3,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset(("GET",)),
                respect_retry_after_header=True,
            )
            session.mount("https://", HTTPAdapter(max_retries=politica))
        self.session = session

    def consultar(self, cep_oito_digitos: str) -> ResultadoCEP:
        if cep_oito_digitos in self.cache:
            c = self.cache[cep_oito_digitos]
            return ResultadoCEP(c.get("bairro"), c["status"], "ViaCEP (cache)", c.get("uf"))
        try:
            res = self.session.get(f"https://viacep.com.br/ws/{cep_oito_digitos}/json/", timeout=5)
            res.raise_for_status()
            dados = res.json()
            if not isinstance(dados, dict):
                raise ValueError("Resposta da API não é objeto JSON")
            # O ViaCEP pode retornar o marcador como booleano True ou string "true".
            if str(dados.get("erro")).strip().lower() == "true":
                resultado = ResultadoCEP(None, "NAO_ENCONTRADO")
            elif dados.get("cep") or "bairro" in dados or "logradouro" in dados:
                resultado = ResultadoCEP(
                    limpo(dados.get("bairro")) or None,
                    "OK", "ViaCEP", limpo(dados.get("uf")) or None,
                )
            else:
                raise ValueError("Resposta incompleta da API")
            self.cache[cep_oito_digitos] = {
                "bairro": resultado.bairro, "status": resultado.status, "uf": resultado.uf,
            }
            return resultado
        except Exception as exc:
            # Não confundir timeouts, HTTP 429/5xx e conexão com CEP inexistente.
            resposta_http = getattr(exc, "response", None)
            codigo_http = getattr(resposta_http, "status_code", None)
            diagnostico = (f"HTTP {codigo_http}" if codigo_http is not None
                           else type(exc).__name__)
            return ResultadoCEP(None, "INDISPONIVEL", f"ViaCEP ({diagnostico})")

    def salvar_cache(self):
        self.caminho_cache.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".tmp", dir=self.caminho_cache.parent, delete=False,
        ) as tmp:
            json.dump(self.cache, tmp, ensure_ascii=False, indent=2, sort_keys=True)
            caminho_temporario = Path(tmp.name)
        caminho_temporario.replace(self.caminho_cache)


def extrair_csv(caminho: Path) -> pd.DataFrame:
    df = pd.read_csv(caminho, sep=";", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    faltando = set(COLUNAS_OBRIGATORIAS) - set(df.columns)
    if faltando:
        raise ValueError(f"CSV sem colunas obrigatórias: {', '.join(sorted(faltando))}")
    ids = df["id_cliente"].str.strip()
    if (ids == "").any():
        raise ValueError("Cliente sem id_cliente")
    if ids.duplicated().any():
        raise ValueError("ID de cliente repetido no CSV")
    return df


def transformar(
    origem: pd.DataFrame,
    consulta_cep: Callable[[str], ResultadoCEP] | None = None,
    execucao_id: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Aplica regras sem efeito colateral. `consulta_cep` pode ser um mock."""
    execucao_id = execucao_id or str(uuid4())
    nomes_vendedores = sorted({limpo(v) for v in origem["vendedor_responsavel"]} - {""})
    ids_vendedor = {nome: numero for numero, nome in enumerate(nomes_vendedores, 1)}
    contagem_emails = Counter(
        email for bruto in origem["email"]
        if (email := normalizar_email(bruto)[0]) is not None
    )
    clientes, auditoria, pendencias, eventos = [], [], [], Counter()
    consultas_cache: dict[str, ResultadoCEP] = {}

    def registrar(ident, campo, original, tratado, criterio, fonte, status="NORMALIZADO", forcar=False):
        if forcar or limpo(original) != limpo(tratado) or status != "NORMALIZADO":
            auditoria.append({
                "execucao_id": execucao_id, "id_cliente": ident, "campo": campo,
                "valor_original": limpo(original), "valor_tratado": limpo(tratado),
                "criterio": criterio, "fonte": fonte, "status": status,
            })

    for _, entrada in origem.iterrows():
        ident = limpo(entrada["id_cliente"])
        alertas: list[str] = []

        def pendente(motivo):
            if motivo not in alertas:
                alertas.append(motivo)
            eventos[motivo] += 1

        tratado = {
            "id_cliente": ident,
            "razao_social": limpo(entrada["razao_social"]),
            "cidade": limpo(entrada["cidade"]),
            "uf": limpo(entrada["uf"]).upper(),
        }
        for original, saida, funcao, regra in (
            ("cnpj", "cnpj_normalizado", normalizar_cnpj, "Máscara de CNPJ fictício com 14 dígitos"),
            ("telefone", "telefone_normalizado", normalizar_telefone, "DDD + número e DDI 55 opcional"),
            ("email", "email", normalizar_email, "Caixa baixa, verificação sintática sem adivinhar domínio"),
        ):
            valor, status = funcao(entrada[original])
            tratado[saida] = valor
            registrar(ident, original, entrada[original], valor, regra, "Regra ETL", status if status != "OK" else "NORMALIZADO")
            if status != "OK":
                pendente(status)

        email = tratado["email"]
        tratado["email_compartilhado"] = bool(email and contagem_emails[email] > 1)
        if tratado["email_compartilhado"]:
            eventos["EMAIL_COMPARTILHADO"] += 1
            registrar(ident, "email", entrada["email"], email,
                      "E-mail pode ser compartilhado; não impor UNIQUE", "Verificação CSV", "INFORMATIVO", True)

        iso, status_data = normalizar_data(entrada["data_cadastro"])
        br = formatar_data_br(iso)
        tratado["data_cadastro_normalizado"] = br
        tratado["data_cadastro_iso"] = iso
        registrar(ident, "data_cadastro", entrada["data_cadastro"], br,
                  "Apresentação DD/MM/AAAA; DateField recebe ISO", "Regra ETL",
                  status_data if status_data != "OK" else "NORMALIZADO")
        if status_data != "OK":
            pendente(status_data)

        nome_vendedor = limpo(entrada["vendedor_responsavel"])
        tratado["vendedor_id"] = ids_vendedor.get(nome_vendedor)
        if not nome_vendedor:
            pendente("SEM_VENDEDOR")
        registrar(ident, "vendedor_responsavel", entrada["vendedor_responsavel"], tratado["vendedor_id"],
                  "Relação com vendedor", "CSV e dicionário de vendedores")

        bairro = normalizar_bairro(entrada["bairro_informado"])
        tratado["bairro_informado"] = limpo(entrada["bairro_informado"]) or None
        if bairro is None:
            pendente("BAIRRO_AUSENTE" if not tratado["bairro_informado"] else "BAIRRO_NAO_MAPEADO")

        cep, cep_sintaxe = normalizar_cep(entrada["cep"])
        tratado["cep_original"] = limpo(entrada["cep"]) or None
        tratado["cep_normalizado"] = cep
        tratado["bairro_normalizado"] = bairro  # Nunca trocar por sugestão da API.
        tratado["bairro_via_cep"] = None
        tratado["status_cep_api"] = "NAO_CONSULTADO" if cep else "SEM_CEP_VALIDO"
        tratado["cep_confirmado_via_cep"] = False

        if cep_sintaxe != "OK":
            pendente("CEP_" + cep_sintaxe)
            status_cep = cep_sintaxe
            consistencia = "NAO_AVALIAVEL"
            fonte = "Regra ETL (sem consulta)"
        elif consulta_cep is None:
            status_cep = "NAO_CONSULTADO"
            consistencia = "NAO_VERIFICADA"
            eventos["CEP_NAO_CONSULTADO"] += 1
            fonte = "Regra ETL (somente formato)"
        else:
            chave = cep.replace("-", "")
            if chave not in consultas_cache:
                consultas_cache[chave] = consulta_cep(chave)
            resposta = consultas_cache[chave]
            tratado["bairro_via_cep"] = resposta.bairro
            tratado["status_cep_api"] = resposta.status
            fonte = resposta.fonte
            if resposta.status == "OK":
                status_cep = "LOCALIZADO"
                tratado["cep_confirmado_via_cep"] = True  # Existência no serviço, não endereço do cliente.
                bairro_api = normalizar_bairro(resposta.bairro)
                if resposta.uf and resposta.uf.upper() != tratado["uf"]:
                    consistencia = "DIVERGENTE_UF"
                    pendente("CONFLITO_CEP_UF")
                elif bairro is None or not resposta.bairro or bairro_api is None:
                    consistencia = "NAO_AVALIAVEL"
                    if resposta.bairro and bairro_api is None:
                        # Ex.: ViaCEP informa Areal, mas o cadastro Águas Claras.
                        # Areal está na atual RA Arniqueira; não tratar como
                        # sinônimo automático de Águas Claras nem como erro certo.
                        pendente("BAIRRO_API_NAO_MAPEADO")
                elif bairro == bairro_api:
                    consistencia = "COMPATIVEL"
                else:
                    consistencia = "DIVERGENTE_BAIRRO"
                    pendente("CONFLITO_CEP_BAIRRO")
            elif resposta.status == "NAO_ENCONTRADO":
                status_cep = "NAO_LOCALIZADO"
                consistencia = "NAO_AVALIAVEL"
                pendente("CEP_NAO_LOCALIZADO")
            else:
                status_cep = "API_INDISPONIVEL"
                consistencia = "NAO_VERIFICADA"
                pendente("API_INDISPONIVEL")

        # Mantém CEP de 8 dígitos mesmo quando ViaCEP não o localiza: status deixa claro
        # que é um valor informado e NÃO confirmado. Só CEP malformado/zerado vira NULL.
        tratado["status_cep"] = status_cep
        tratado["status_consistencia"] = consistencia
        tratado["cep_origem"] = "CADASTRO" if cep else "AUSENTE_OU_INVALIDO"
        tratado["pendencia_revisao"] = bool(alertas)
        tratado["motivos_pendencia"] = ";".join(alertas)

        registrar(ident, "cep", entrada["cep"], cep,
                  "Preservar CEP com 8 dígitos mesmo não localizado; 00000-000 vira NULL; jamais preencher por bairro",
                  fonte, status_cep, True)
        registrar(ident, "bairro_informado", entrada["bairro_informado"], bairro,
                  "Agrupamento canônico do bairro do cadastro; não substituir por bairro API",
                  "Cadastro + dicionário ETL", "REVISAR" if bairro is None else "NORMALIZADO", True)
        if cep and consulta_cep is not None:
            # Consulta e comparação NÃO são transformações do bairro retornado.
            # Não registrar o bairro do cadastro como "valor tratado" do ViaCEP:
            # isso indicaria uma substituição que nunca ocorreu.
            bairro_consultado = tratado["bairro_via_cep"]
            criterio_comparacao = (
                f"Comparar bairro retornado pelo ViaCEP com bairro normalizado "
                f"do cadastro ({bairro or 'ausente'}); preservar ambos os valores "
                f"e sinalizar divergências sem substituição automática"
            )
            registrar(ident, "bairro_via_cep", bairro_consultado, bairro_consultado,
                      criterio_comparacao, fonte,
                      "CONFLITO" if consistencia.startswith("DIVERGENTE_") else consistencia,
                      True)
        if alertas:
            pendencias.append({
                "id_cliente": ident, "bairro_informado": tratado["bairro_informado"],
                "bairro_normalizado": bairro, "cep_original": tratado["cep_original"],
                "cep_normalizado": cep, "bairro_via_cep": tratado["bairro_via_cep"],
                "status_cep": status_cep, "status_consistencia": consistencia,
                "motivos": tratado["motivos_pendencia"],
            })
        clientes.append(tratado)

    df_clientes = pd.DataFrame(clientes)
    df_vendedores = pd.DataFrame([
        {"id_vendedor": id_, "nome_vendedor": nome} for nome, id_ in ids_vendedor.items()
    ])
    df_auditoria = pd.DataFrame(auditoria, columns=[
        "execucao_id", "id_cliente", "campo", "valor_original", "valor_tratado",
        "criterio", "fonte", "status",
    ])
    df_pendencias = pd.DataFrame(pendencias, columns=[
        "id_cliente", "bairro_informado", "bairro_normalizado", "cep_original",
        "cep_normalizado", "bairro_via_cep", "status_cep", "status_consistencia", "motivos",
    ])
    contagem_bairros = df_clientes["bairro_normalizado"].value_counts(dropna=False).to_dict()
    resumo = {
        "execucao_id": execucao_id,
        "clientes_lidos": len(origem),
        "clientes_tratados": len(df_clientes),
        "vendedores": len(df_vendedores),
        "bairros_canonicos": {
            "SEM_BAIRRO" if pd.isna(k) else str(k): int(v) for k, v in contagem_bairros.items()
        },
        "registros_com_pendencia": len(df_pendencias),
        "linhas_auditoria": len(df_auditoria),
        "ceps_por_status": {str(k): int(v) for k, v in df_clientes["status_cep"].value_counts().items()},
        "ocorrencias": dict(sorted(eventos.items())),
    }
    return df_clientes, df_vendedores, df_auditoria, df_pendencias, resumo


def salvar_csv_e_relatorio(clientes, vendedores, auditoria, pendencias, resumo, pasta: Path) -> None:
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, df in (
        ("clientes_tratados.csv", clientes),
        ("vendedores.csv", vendedores),
        ("auditoria_etl.csv", auditoria),
        ("pendencias_revisao.csv", pendencias),
    ):
        df.to_csv(pasta / nome, sep=";", index=False, encoding="utf-8-sig")
    (pasta / "resumo_etl.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main():
    raiz = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="ETL Primora: CSV → limpeza → auditoria → CSV")
    parser.add_argument("--csv", type=Path, default=raiz / "02-clientes_distribuidora_vetor.csv")
    parser.add_argument("--saida", type=Path, default=raiz / "resultados")
    parser.add_argument("--consultar-cep", action="store_true", help="Habilita consulta ao ViaCEP; padrão é offline")
    parser.add_argument("--cache", type=Path, help="Local do cache JSON da API")
    args = parser.parse_args()
    entrada = extrair_csv(args.csv)
    cliente_api = ClienteViaCEP(args.cache or args.saida / "cache_viacep.json") if args.consultar_cep else None
    resultado = transformar(entrada, consulta_cep=cliente_api.consultar if cliente_api else None)
    salvar_csv_e_relatorio(*resultado, pasta=args.saida)
    if cliente_api:
        cliente_api.salvar_cache()
    print(json.dumps(resultado[-1], ensure_ascii=False, indent=2))
    print("Arquivos em:", args.saida.resolve())


if __name__ == "__main__":
    main()
