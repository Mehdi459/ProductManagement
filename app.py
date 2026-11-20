"""Interface graphique BookForge.  Lancer :  streamlit run app.py"""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from bookforge import config, course, export, illustrations, pipeline, trends, writer
from bookforge.llm import GenerationError
from bookforge.project import BookProject, list_projects

st.set_page_config(page_title="BookForge", page_icon="📚", layout="wide")
st.title("📚 BookForge — livres, formations et étude de marché")

if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
    st.warning("Définissez la variable d'environnement ANTHROPIC_API_KEY avant de générer du contenu.")

ss = st.session_state
ss.setdefault("projet", None)
ss.setdefault("marche", None)
ss.setdefault("idee", {})

# ---------------- Barre latérale : projets ----------------
with st.sidebar:
    st.header("Projets")
    paths = list_projects()
    choix = st.selectbox("Ouvrir un projet", ["—"] + [str(p) for p in paths],
                         format_func=lambda x: x if x == "—" else BookProject.load(x).titre)
    if choix != "—" and st.button("Ouvrir"):
        ss.projet = BookProject.load(choix)
    p: BookProject | None = ss.projet
    if p:
        st.success(f"**{p.titre}**")
        ecrits = sum(1 for c in p.chapitres for s in c.sections if s.texte)
        total = sum(len(c.sections) for c in p.chapitres) or 1
        st.progress(ecrits / total, f"{ecrits}/{total} sections")
        st.metric("Pages estimées", f"{p.pages} / {p.pages_cible}")
        st.metric("Mots", f"{p.mots:,}".replace(",", " "))
    st.caption(f"Modèle : {config.MODEL}")


def guard(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except GenerationError as e:
        st.error(str(e))
    except Exception as e:  # erreurs réseau / API
        st.error(f"Erreur : {e}")


tabs = st.tabs(["🔎 Tendances", "✍️ Nouveau livre", "📖 Écriture", "🎨 Illustrations & couvertures",
                "🎓 Formation", "💶 Prix", "📦 Exports"])

# ---------------- 1. Tendances ----------------
with tabs[0]:
    st.subheader("Livres les plus vendus et sujets porteurs")
    c1, c2, c3 = st.columns(3)
    g = c1.selectbox("Genre", ["tous genres"] + list(config.GENRES.values()))
    langue = c2.text_input("Langue", "français")
    marche = c3.text_input("Marché", "France")
    kw = st.text_input("Mots-clés / centres d'intérêt (optionnel)")
    if st.button("Lancer l'étude de marché", type="primary"):
        with st.spinner("Recherche sur Amazon, Fnac, Babelio, Udemy, Skillshare… (1 à 3 min)"):
            ss.marche = guard(trends.market_research, g, langue, marche, kw)
    m = ss.marche
    if m:
        st.info(m.get("synthese", ""))
        st.markdown("#### 🏆 Best-sellers")
        st.dataframe(pd.DataFrame(m.get("best_sellers", [])), use_container_width=True)
        st.markdown("#### 📈 Tendances")
        df_t = pd.DataFrame(m.get("tendances", []))
        if not df_t.empty and "score_tendance" in df_t:
            st.bar_chart(df_t.set_index("sujet")["score_tendance"])
        st.dataframe(df_t, use_container_width=True)
        st.markdown("#### 🎓 Formations populaires")
        st.dataframe(pd.DataFrame(m.get("formations_populaires", [])), use_container_width=True)
        st.markdown("#### 💡 Idées de livres à fort potentiel")
        for i, idee in enumerate(m.get("idees_de_livres", [])):
            with st.expander(f"{idee.get('potentiel', '?')}/100 — {idee.get('titre')}"):
                st.write(f"*{idee.get('sous_titre', '')}*")
                st.write(f"**Public :** {idee.get('public_cible', '')}")
                st.write(f"**Angle unique :** {idee.get('angle_unique', '')}")
                st.write(f"**Formation associée :** {idee.get('formation_associee', '')}")
                if st.button("Utiliser cette idée", key=f"idee{i}"):
                    ss.idee = idee
                    st.success("Idée copiée dans l'onglet « Nouveau livre ».")

# ---------------- 2. Nouveau livre ----------------
with tabs[1]:
    idee = ss.idee
    with st.form("nouveau"):
        titre = st.text_input("Titre provisoire", idee.get("titre", ""))
        keys = list(config.GENRES)
        genre = st.selectbox("Type de livre", keys, format_func=config.GENRES.get)
        sujet = st.text_area("Sujet, pitch, intrigue ou thèse",
                             " — ".join(x for x in (idee.get("sous_titre"), idee.get("angle_unique")) if x), height=120)
        c1, c2, c3 = st.columns(3)
        pages = c1.number_input("Nombre de pages visé", 20, 900, 200, step=10)
        public = c2.text_input("Public", idee.get("public_cible", "adultes"))
        auteur = c3.text_input("Nom d'auteur", "Auteur")
        ton = st.text_input("Ton / style (optionnel)", placeholder="ex. humour, style Agatha Christie, très pédagogique…")
        illustre = st.checkbox("Avec illustrations", True)
        go = st.form_submit_button("Créer le plan détaillé", type="primary")
    if go and titre and sujet:
        p = BookProject(titre=titre, genre=genre, sujet=sujet, pages_cible=int(pages), public=public,
                        auteur=auteur, ton=ton, illustre=illustre, marche=ss.marche or {})
        with st.spinner("Conception du plan et de la bible de continuité…"):
            if guard(writer.create_outline, p):
                ss.projet = p
                st.rerun()
    p = ss.projet
    if p and p.chapitres:
        st.markdown(f"### {p.titre}\n*{p.sous_titre}*")
        st.caption(f"{len(p.chapitres)} chapitres · ~{p.mots_cible:,} mots visés".replace(",", " "))
        with st.expander("Bible de continuité (modifiable)"):
            bible = st.text_area("Bible", p.bible, height=300, label_visibility="collapsed")
            if st.button("Enregistrer la bible"):
                p.bible = bible
                p.save()
        for c in p.chapitres:
            st.markdown(f"**{c.numero}. {c.titre}** — {c.resume}")

# ---------------- 3. Écriture ----------------
with tabs[2]:
    p = ss.projet
    if not p or not p.chapitres:
        st.info("Créez d'abord un livre dans l'onglet « Nouveau livre ».")
    else:
        st.write("La rédaction se fait section par section et est sauvegardée en continu : "
                 "vous pouvez interrompre et reprendre à tout moment.")
        c1, c2 = st.columns(2)
        if c1.button("✍️ Écrire tout le livre", type="primary"):
            bar = st.progress(0.0)
            live = st.empty()
            buf = []

            def on_text(t):
                buf.append(t)
                live.markdown("".join(buf)[-1500:])

            def prog(f, msg):
                buf.clear()
                bar.progress(min(f, 1.0), msg)

            guard(writer.write_book, p, progress=prog, on_text=on_text)
            st.success("Manuscrit terminé !")
        if c2.button("🚀 Tout générer (livre + illustrations + couvertures + formation + prix + exports)"):
            bar = st.progress(0.0)
            files = guard(pipeline.run_all, p, etude_marche=not p.marche,
                          progress=lambda f, m: bar.progress(min(f, 1.0), m))
            if files:
                st.success("Tout est prêt — voir l'onglet Exports.")
        for c in p.chapitres:
            etat = "✅" if c.done else "⏳"
            with st.expander(f"{etat} Chapitre {c.numero} — {c.titre} ({c.mots} mots)"):
                for i, s in enumerate(c.sections):
                    st.markdown(f"##### {s.titre}")
                    if s.texte:
                        st.markdown(s.texte)
                    if st.button("Écrire" if not s.texte else "Réécrire", key=f"w{c.numero}-{i}"):
                        with st.spinner("Rédaction…"):
                            guard(writer.write_section, p, c, i)
                        st.rerun()

# ---------------- 4. Illustrations & couvertures ----------------
with tabs[3]:
    p = ss.projet
    if not p or not p.chapitres:
        st.info("Créez d'abord un livre.")
    else:
        c1, c2, c3 = st.columns(3)
        if c1.button("🎨 Couverture"):
            with st.spinner("Création de la couverture…"):
                guard(illustrations.make_cover, p)
        if c2.button("📝 Quatrième de couverture"):
            with st.spinner("Rédaction…"):
                guard(illustrations.write_back_cover, p)
        if c3.button("🖼️ Illustrer tous les chapitres"):
            bar = st.progress(0.0)
            guard(illustrations.illustrate_all, p, progress=lambda f, m: bar.progress(f, m))
        cc1, cc2 = st.columns(2)
        if p.couverture_svg:
            cc1.markdown("**Couverture**")
            cc1.image(p.couverture_svg, use_container_width=True)
        if p.quatrieme:
            cc2.markdown("**Quatrième de couverture**")
            q = cc2.text_area("4e", p.quatrieme, height=400, label_visibility="collapsed")
            if cc2.button("Enregistrer la 4e"):
                p.quatrieme = q
                p.save()
        cols = st.columns(3)
        for i, c in enumerate(p.chapitres):
            with cols[i % 3]:
                st.caption(f"Ch. {c.numero} — {c.titre}")
                if c.illustration_svg:
                    st.image(c.illustration_svg, use_container_width=True)
                if st.button("Illustrer" if not c.illustration_svg else "Refaire", key=f"il{c.numero}"):
                    with st.spinner("Illustration…"):
                        guard(illustrations.illustrate_chapter, p, c)
                    st.rerun()

# ---------------- 5. Formation ----------------
with tabs[4]:
    p = ss.projet
    if not p or not p.chapitres:
        st.info("Créez d'abord un livre.")
    else:
        if st.button("🎓 Générer la formation Udemy + Skillshare", type="primary"):
            with st.spinner("Conception pédagogique…"):
                guard(course.make_course, p)
        if p.formation:
            st.markdown(export.course_markdown(p))

# ---------------- 6. Prix ----------------
with tabs[5]:
    p = ss.projet
    if not p:
        st.info("Créez d'abord un livre.")
    else:
        if st.button("💶 Calculer les prix", type="primary") or not p.prix:
            pipeline.update_prices(p)
        pr = p.prix
        c1, c2, c3 = st.columns(3)
        c1.metric("Ebook", f"{pr['ebook']['prix']:.2f} €", f"{pr['ebook']['redevance_par_vente']:.2f} € / vente")
        c2.metric("Broché", f"{pr['broche']['prix']:.2f} €", f"{pr['broche']['redevance_par_vente']:.2f} € / vente")
        c3.metric("Formation Udemy", f"{pr['udemy']['prix_catalogue']:.2f} €",
                  f"{pr['udemy']['revenu_vente_marketplace']:.2f} € / vente marketplace")
        st.caption(f"Coût d'impression estimé : {pr['broche']['cout_impression']:.2f} € — {pr['avertissement']}")
        st.markdown("#### Projection de revenus mensuels")
        st.dataframe(pd.DataFrame(pr.get("scenarios", [])), use_container_width=True)

# ---------------- 7. Exports ----------------
with tabs[6]:
    p = ss.projet
    if not p:
        st.info("Créez d'abord un livre.")
    elif st.button("📦 Exporter (PDF, Word, HTML, Markdown, formation)", type="primary"):
        files = guard(export.export_all, p)
        for k, path in (files or {}).items():
            st.download_button(f"Télécharger {k} ({path.name})", path.read_bytes(), file_name=path.name, key=k)
