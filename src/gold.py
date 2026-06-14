"""Gold: star schema (dimensões + fatos) + entregáveis analíticos.

Fluxo:  silver dict -> dim_* + fato_* -> gold_* (entregáveis)

Construído em ETAPAS na trilha:
  ETAPA 1 (este arquivo): dimensões.
  ETAPA 2: fatos.
  ETAPA 3: os 6 entregáveis.

Em produção (Databricks) cada DataFrame vira uma tabela Delta no Volume.
"""
import pandas as pd


def _select(df, cols):
    """Seleciona só as colunas que existem — evita KeyError se a API variar."""
    return df[[c for c in cols if c in df.columns]].copy()


# ----------------------------------------------------------------------
# ETAPA 1 — Dimensões (uma linha por entidade; descritivas, sem cálculo)
# ----------------------------------------------------------------------

def dim_deputado(silver):
    """Quem é cada parlamentar."""
    return _select(silver["deputados"], [
        "id_deputado", "nome", "sigla_partido", "sigla_uf", "id_legislatura", "email",
    ])


def dim_partido(silver):
    """Catálogo de partidos."""
    return _select(silver["partidos"], ["id_partido", "sigla_partido", "nome_partido"])


def dim_frente(silver):
    """Catálogo de frentes parlamentares."""
    return _select(silver["frentes"], ["id_frente", "nome_frente", "id_legislatura"])


def dim_orgao(silver):
    """Órgãos: comissões, conselhos, CPIs, Plenário."""
    return _select(silver["orgaos"], [
        "id_orgao", "sigla_orgao", "nome_orgao", "tipo_orgao", "cod_tipo_orgao",
    ])


def dim_evento(silver):
    """Eventos: sessões, audiências, reuniões."""
    return _select(silver["eventos"], [
        "id_evento", "data_hora_inicio", "data_hora_fim", "descricao_tipo", "situacao",
    ])


def build_dims(silver):
    """Monta todas as dimensões. Retorna dict nome -> DataFrame."""
    return {
        "dim_deputado": dim_deputado(silver),
        "dim_partido": dim_partido(silver),
        "dim_frente": dim_frente(silver),
        "dim_orgao": dim_orgao(silver),
        "dim_evento": dim_evento(silver),
    }


# ----------------------------------------------------------------------
# ETAPA 2 — Fatos (uma linha por evento medido; só IDs + medidas)
# ----------------------------------------------------------------------

def fato_voto(silver):
    """Grão: um voto = (votação × deputado)."""
    return _select(silver["votacao_votos"], [
        "id_votacao", "id_deputado", "tipo_voto", "data_registro_voto",
    ])


def fato_presenca(silver):
    """Grão: uma presença = (evento × deputado)."""
    return _select(silver["evento_deputados"], [
        "id_evento", "id_deputado", "sigla_partido", "sigla_uf",
    ])


def fato_despesa(silver):
    """Grão: uma despesa = (deputado × documento). Medida: valor_liquido."""
    return _select(silver["deputado_despesas"], [
        "id_deputado", "ano", "mes", "tipo_despesa", "valor_liquido",
        "nome_fornecedor", "cnpj_fornecedor", "data_documento",
    ])


def build_facts(silver):
    """Monta todos os fatos. Retorna dict nome -> DataFrame."""
    return {
        "fato_voto": fato_voto(silver),
        "fato_presenca": fato_presenca(silver),
        "fato_despesa": fato_despesa(silver),
    }


# ----------------------------------------------------------------------
# ETAPA 3 — Entregáveis analíticos
# ----------------------------------------------------------------------

# --- Entregável 1: Atlas das frentes (diversidade via Herfindahl) ---

def gold_atlas_frentes(silver):
    """Junta frentes + membros + deputado (partido/UF). Uma linha por membro."""
    fr = silver["frentes"][["id_frente", "nome_frente", "id_legislatura"]]
    fm = silver["frente_membros"][["id_frente", "id_deputado"]]
    dep = silver["deputados"][["id_deputado", "nome", "sigla_partido", "sigla_uf"]]
    return (fm.merge(dep, on="id_deputado", how="left")
              .merge(fr, on="id_frente", how="left"))


def gold_frente_diversidade_hhi(atlas):
    """Índice de Herfindahl por frente: soma dos quadrados das participações.

    HHI baixo  = muitos partidos equilibrados (diverso).
    HHI alto   = um partido domina (concentrado). HHI=1 -> partido único.
    """
    rows = []
    for fid, grp in atlas.groupby("id_frente"):
        total = len(grp)
        if total == 0:
            continue
        share = grp["sigla_partido"].fillna("?").value_counts() / total
        rows.append({
            "id_frente": fid,
            "nome_frente": grp["nome_frente"].iloc[0],
            "n_membros": int(total),
            "n_partidos": int(grp["sigla_partido"].nunique()),
            "n_ufs": int(grp["sigla_uf"].fillna("?").nunique()),
            "hhi": float((share ** 2).sum()),
        })
    return pd.DataFrame(rows).sort_values("hhi").reset_index(drop=True)


def gold_deputados_em_n_frentes(atlas, top=20):
    """Top deputados pelo número de frentes em que participam."""
    return (atlas.groupby(["id_deputado", "nome", "sigla_partido", "sigla_uf"])
                 .size().reset_index(name="n_frentes")
                 .sort_values("n_frentes", ascending=False)
                 .head(top).reset_index(drop=True))


# --- Entregável 2: Calendário de eventos ---

def gold_taxa_presenca(silver):
    """Taxa de presença por deputado = presenças / total de eventos."""
    total_eventos = silver["eventos"]["id_evento"].nunique()
    if total_eventos == 0:
        return pd.DataFrame()
    pres = (silver["evento_deputados"].groupby("id_deputado")
            .size().reset_index(name="n_presencas"))
    pres["total_eventos"] = total_eventos
    pres["taxa_presenca"] = pres["n_presencas"] / total_eventos
    dep = silver["deputados"][["id_deputado", "nome", "sigla_partido", "sigla_uf"]]
    return (pres.merge(dep, on="id_deputado", how="left")
                .sort_values("taxa_presenca", ascending=False).reset_index(drop=True))


def gold_densidade_semanal(silver):
    """Quantidade de eventos por semana ISO (ano, semana)."""
    df = silver["eventos"].copy()
    df["data_hora_inicio"] = pd.to_datetime(df["data_hora_inicio"], errors="coerce", utc=True)
    df = df.dropna(subset=["data_hora_inicio"])
    df["ano"] = df["data_hora_inicio"].dt.isocalendar().year
    df["semana"] = df["data_hora_inicio"].dt.isocalendar().week
    return (df.groupby(["ano", "semana"]).size().reset_index(name="qtd_eventos")
              .sort_values(["ano", "semana"]).reset_index(drop=True))


def gold_eventos_futuros(silver):
    """Calendário público: eventos com data de início no futuro."""
    df = silver["eventos"].copy()
    df["data_hora_inicio"] = pd.to_datetime(df["data_hora_inicio"], errors="coerce", utc=True)
    futuros = df[df["data_hora_inicio"] > pd.Timestamp.utcnow()].copy()
    return futuros.sort_values("data_hora_inicio").reset_index(drop=True)


# --- Entregável 3: Correlação frente x votação (alinhamento) ---

def _alinhamento_por_grupo(votos, group_col):
    """Para cada votação+grupo, % do voto majoritário (só Sim/Não).

    alinhamento = max(Sim, Não) / total. 1.0 = grupo unânime.
    """
    df = votos[votos["tipo_voto"].isin(["Sim", "Nao"])].copy()
    if df.empty:
        return pd.DataFrame()
    grupo = df.groupby(["id_votacao", group_col, "tipo_voto"]).size().reset_index(name="n")
    pivot = grupo.pivot_table(index=["id_votacao", group_col], columns="tipo_voto",
                              values="n", fill_value=0).reset_index()
    for c in ["Sim", "Nao"]:
        if c not in pivot.columns:
            pivot[c] = 0
    pivot["total"] = pivot["Sim"] + pivot["Nao"]
    pivot = pivot[pivot["total"] >= 2].copy()
    pivot["alinhamento"] = pivot[["Sim", "Nao"]].max(axis=1) / pivot["total"]
    return pivot


def gold_alinhamento_frente_vs_partido(silver):
    """Compara alinhamento médio dentro de frentes vs dentro de partidos.

    Responde: deputados da mesma frente votam mais juntos que os do mesmo partido?
    Retorna (resumo_frente, resumo_partido).
    """
    votos = silver["votacao_votos"].copy()

    ali_partido = _alinhamento_por_grupo(votos, "sigla_partido")
    resumo_partido = (ali_partido.groupby("sigla_partido")
                      .agg(alinhamento_medio=("alinhamento", "mean"),
                           qtd_votacoes=("id_votacao", "nunique"))
                      .reset_index().sort_values("alinhamento_medio", ascending=False))

    fm = silver["frente_membros"][["id_frente", "id_deputado"]]
    votos_frente = votos.merge(fm, on="id_deputado")
    ali_frente = _alinhamento_por_grupo(votos_frente, "id_frente")
    fr = silver["frentes"][["id_frente", "nome_frente"]]
    resumo_frente = (ali_frente.groupby("id_frente")
                     .agg(alinhamento_medio=("alinhamento", "mean"),
                          qtd_votacoes=("id_votacao", "nunique"))
                     .reset_index().merge(fr, on="id_frente", how="left")
                     .sort_values("alinhamento_medio", ascending=False))

    return resumo_frente, resumo_partido


# --- Entregável 4: Raio-X CEAP ---

def gold_ceap_ranking_fornecedor(silver, top_n=100):
    """Top fornecedores por valor total recebido."""
    df = silver["deputado_despesas"].copy()
    if df.empty:
        return pd.DataFrame()
    return (df.groupby(["cnpj_fornecedor", "nome_fornecedor"], dropna=False)
              .agg(valor_total=("valor_liquido", "sum"),
                   qtd_documentos=("cod_documento", "count"),
                   qtd_deputados=("id_deputado", "nunique"))
              .reset_index().sort_values("valor_total", ascending=False)
              .head(top_n).reset_index(drop=True))


def gold_ceap_mensal_partido(silver):
    """Total gasto por partido, por mês (relatório mensal)."""
    df = silver["deputado_despesas"].copy()
    if df.empty:
        return pd.DataFrame()
    dep = silver["deputados"][["id_deputado", "sigla_partido"]]
    df = df.merge(dep, on="id_deputado", how="left")
    return (df.groupby(["ano", "mes", "sigla_partido"])
              .agg(total=("valor_liquido", "sum"), qtd=("cod_documento", "count"))
              .reset_index()
              .sort_values(["ano", "mes", "total"], ascending=[True, True, False])
              .reset_index(drop=True))


def gold_ceap_anomalia_zscore(silver, z_thresh=3.0):
    """Detecção de anomalia por z-score: categoria (tipo_despesa) × UF do deputado.

    z = (valor - média_do_grupo) / desvio_do_grupo. |z| > 3 = gasto atípico
    frente aos pares do mesmo estado e mesma categoria. Atende o requisito de
    'score de anomalia' do desafio.
    """
    df = silver["deputado_despesas"].copy()
    if df.empty:
        return pd.DataFrame()
    dep = silver["deputados"][["id_deputado", "nome", "sigla_partido", "sigla_uf"]]
    df = df.merge(dep, on="id_deputado", how="left")

    grupo = df.groupby(["tipo_despesa", "sigla_uf"])["valor_liquido"]
    df["media_grupo"] = grupo.transform("mean")
    df["desvio_grupo"] = grupo.transform("std")
    # z-score (desvio 0/nulo -> z fica nulo, não é anomalia)
    df["zscore"] = (df["valor_liquido"] - df["media_grupo"]) / df["desvio_grupo"]
    df["anomalia"] = df["zscore"].abs() > z_thresh

    cols = ["id_deputado", "nome", "sigla_partido", "sigla_uf", "tipo_despesa",
            "valor_liquido", "media_grupo", "desvio_grupo", "zscore",
            "nome_fornecedor", "cnpj_fornecedor", "data_documento"]
    cols = [c for c in cols if c in df.columns]
    return (df[df["anomalia"]].sort_values("zscore", ascending=False)[cols]
            .reset_index(drop=True))


# --- Entregável 5: Auditoria de CPIs ---

def gold_cpis(silver):
    """Órgãos que são CPI/CPMI + duração e se excederam prazo regimental (180 dias).

    Heurística: nome contém 'CPI', 'CPMI' ou 'Inquérito'. Limitação conhecida:
    a API expõe sobretudo órgãos ativos da legislatura — CPIs antigas podem faltar.
    """
    df = silver["orgaos"].copy()
    mask = df["nome_orgao"].fillna("").str.contains(
        r"CPI|CPMI|Inqu[eé]rito", case=False, regex=True, na=False)
    cpis = df[mask].copy()
    for c in ("data_inicio", "data_fim"):
        if c not in cpis.columns:
            cpis[c] = pd.NaT
    if cpis.empty:
        return pd.DataFrame(columns=["id_orgao", "sigla_orgao", "nome_orgao",
                                     "tipo_orgao", "data_inicio", "data_fim",
                                     "duracao_dias", "excedeu_prazo"])
    cpis["data_inicio"] = pd.to_datetime(cpis["data_inicio"], errors="coerce")
    cpis["data_fim"] = pd.to_datetime(cpis["data_fim"], errors="coerce")
    cpis["duracao_dias"] = (cpis["data_fim"] - cpis["data_inicio"]).dt.days
    cpis["excedeu_prazo"] = cpis["duracao_dias"].fillna(0) > 180
    cols = ["id_orgao", "sigla_orgao", "nome_orgao", "tipo_orgao",
            "data_inicio", "data_fim", "duracao_dias", "excedeu_prazo"]
    return cpis[[c for c in cols if c in cpis.columns]].reset_index(drop=True)


# --- Entregável 6: Engajamento e absenteísmo ---

def gold_engajamento_deputado(silver):
    """Score de engajamento (min-max de presenças + votos), com percentil."""
    dep = silver["deputados"][["id_deputado", "nome", "sigla_partido", "sigla_uf"]]
    pres = (silver["evento_deputados"].groupby("id_deputado")
            .size().reset_index(name="n_presencas"))
    votos = (silver["votacao_votos"].groupby("id_deputado")
             .size().reset_index(name="n_votos"))
    score = (dep.merge(pres, on="id_deputado", how="left")
                .merge(votos, on="id_deputado", how="left"))
    score[["n_presencas", "n_votos"]] = score[["n_presencas", "n_votos"]].fillna(0)

    def _norm(s):
        rng = s.max() - s.min()
        return s * 0.0 if rng == 0 else (s - s.min()) / rng

    score["presencas_norm"] = _norm(score["n_presencas"])
    score["votos_norm"] = _norm(score["n_votos"])
    score["engajamento"] = (score["presencas_norm"] + score["votos_norm"]) / 2
    score["percentil"] = score["engajamento"].rank(pct=True)
    return score.sort_values("engajamento", ascending=False).reset_index(drop=True)


def gold_absenteismo_votacao(silver):
    """Taxa de ausência: votações sem voto registrado / total de votações."""
    dep = silver["deputados"][["id_deputado", "nome", "sigla_partido", "sigla_uf"]]
    total = silver["votacoes"]["id_votacao"].nunique()
    if total == 0:
        return pd.DataFrame()
    votou = (silver["votacao_votos"].groupby("id_deputado")["id_votacao"]
             .nunique().reset_index(name="n_votou"))
    out = dep.merge(votou, on="id_deputado", how="left")
    out["n_votou"] = out["n_votou"].fillna(0).astype(int)
    out["n_ausencias"] = total - out["n_votou"]
    out["taxa_ausencia"] = out["n_ausencias"] / total
    return out.sort_values("taxa_ausencia", ascending=False).reset_index(drop=True)


# ----------------------------------------------------------------------
# Orquestrador — monta tudo de uma vez
# ----------------------------------------------------------------------

def build_all(silver):
    """Monta dimensões + fatos + os 6 entregáveis. Retorna dict nome -> DataFrame."""
    out = {}
    out.update(build_dims(silver))
    out.update(build_facts(silver))

    atlas = gold_atlas_frentes(silver)
    out["gold_atlas_frentes"] = atlas
    out["gold_frente_diversidade_hhi"] = gold_frente_diversidade_hhi(atlas)
    out["gold_deputados_em_n_frentes"] = gold_deputados_em_n_frentes(atlas)

    out["gold_taxa_presenca"] = gold_taxa_presenca(silver)
    out["gold_densidade_semanal"] = gold_densidade_semanal(silver)
    out["gold_eventos_futuros"] = gold_eventos_futuros(silver)

    resumo_frente, resumo_partido = gold_alinhamento_frente_vs_partido(silver)
    out["gold_alinhamento_frente"] = resumo_frente
    out["gold_alinhamento_partido"] = resumo_partido

    out["gold_ceap_ranking_fornecedor"] = gold_ceap_ranking_fornecedor(silver)
    out["gold_ceap_mensal_partido"] = gold_ceap_mensal_partido(silver)
    out["gold_ceap_anomalia_zscore"] = gold_ceap_anomalia_zscore(silver)

    out["gold_cpis"] = gold_cpis(silver)

    out["gold_engajamento"] = gold_engajamento_deputado(silver)
    out["gold_absenteismo"] = gold_absenteismo_votacao(silver)
    return out
