"""
Executive Internationalization (i18n) Engine for Mercurius v2.2.
Provides comprehensive enterprise translation catalogs for English, German, French, Spanish,
Chinese (Simplified), and Japanese, supporting parameter interpolation and pluralization.
"""
from __future__ import annotations
from typing import Dict, Any

class I18nEngine:
    CATALOGS: Dict[str, Dict[str, str]] = {
        "en": {
            "welcome": "Welcome to Mercurius Enterprise Agentic AI Studio",
            "prompt_placeholder": "Ask Mercurius or instruct agent fleet...",
            "status_idle": "Cognitive Loop Idle",
            "status_reasoning": "ReAct Reasoning in Progress...",
            "hitl_title": "Human-in-the-Loop Action Approval Required",
            "hitl_approve": "Approve Action",
            "hitl_reject": "Reject",
            "doctor_optimal": "OPTIMAL (All diagnostic checks passed)",
            "rbac_denied": "RBAC Permission Denied: Tool '{tool}' requires {role} privileges."
        },
        "de": {
            "welcome": "Willkommen im Mercurius Enterprise Agentic AI Studio",
            "prompt_placeholder": "Fragen Sie Mercurius oder steuern Sie die Agenten-Flotte...",
            "status_idle": "Kognitiver Zyklus im Leerlauf",
            "status_reasoning": "ReAct-Schlussfolgerung läuft...",
            "hitl_title": "Freigabe durch menschlichen Operator erforderlich (HITL)",
            "hitl_approve": "Aktion Genehmigen",
            "hitl_reject": "Ablehnen",
            "doctor_optimal": "OPTIMAL (Alle Diagnoseprüfungen erfolgreich)",
            "rbac_denied": "RBAC-Zugriff verweigert: Werkzeug '{tool}' erfordert Rolle {role}."
        },
        "fr": {
            "welcome": "Bienvenue sur le Studio d'IA Agentique Mercurius Entreprise",
            "prompt_placeholder": "Demandez à Mercurius ou donnez des instructions à la flotte...",
            "status_idle": "Boucle cognitive au repos",
            "status_reasoning": "Raisonnement ReAct en cours...",
            "hitl_title": "Approbation humaine requise (HITL)",
            "hitl_approve": "Approuver l'action",
            "hitl_reject": "Rejeter",
            "doctor_optimal": "OPTIMAL (Tous les contrôles ont réussi)",
            "rbac_denied": "Autorisation RBAC refusée : L'outil '{tool}' exige les privilèges {role}."
        },
        "es": {
            "welcome": "Bienvenido al Estudio de IA Agéntica Empresarial Mercury",
            "prompt_placeholder": "Pregunta a Mercurius o instruye a la flota de agentes...",
            "status_idle": "Bucle cognitivo en espera",
            "status_reasoning": "Razonamiento ReAct en curso...",
            "hitl_title": "Aprobación de operador humano requerida (HITL)",
            "hitl_approve": "Aprobar acción",
            "hitl_reject": "Rechazar",
            "doctor_optimal": "ÓPTIMO (Todas las comprobaciones superadas)",
            "rbac_denied": "Permiso RBAC denegado: La herramienta '{tool}' requiere privilegios {role}."
        },
        "zh": {
            "welcome": "欢迎使用 Mercurius 企业级智能体 AI 控制台",
            "prompt_placeholder": "向 Mercurius 提问或调度智能体集群...",
            "status_idle": "认知循环空闲",
            "status_reasoning": "ReAct 认知推理中...",
            "hitl_title": "需要人工在环操作批准 (HITL)",
            "hitl_approve": "批准执行",
            "hitl_reject": "拒绝",
            "doctor_optimal": "系统状态最佳（所有诊断项均通过）",
            "rbac_denied": "RBAC 权限拒绝：工具 '{tool}' 需要 {role} 角色权限。"
        },
        "ja": {
            "welcome": "Mercurius エンタープライズ・エージェント AI スタジオへようこそ",
            "prompt_placeholder": "Mercurius に質問するか、エージェントを指示してください...",
            "status_idle": "認知ループ待機中",
            "status_reasoning": "ReAct 推論実行中...",
            "hitl_title": "人間介入（HITL）アクション承認が必要です",
            "hitl_approve": "実行を承認",
            "hitl_reject": "却下",
            "doctor_optimal": "最適（すべての診断チェックに合格）",
            "rbac_denied": "RBAC 権限エラー: ツール '{tool}' には {role} 権限が必要です。"
        }
    }

    def __init__(self, lang: str = "en"):
        self.lang = lang.lower() if lang.lower() in self.CATALOGS else "en"

    def set_language(self, lang: str):
        if lang.lower() in self.CATALOGS:
            self.lang = lang.lower()

    def t(self, key: str, **kwargs: Any) -> str:
        catalog = self.CATALOGS.get(self.lang, self.CATALOGS["en"])
        template = catalog.get(key, self.CATALOGS["en"].get(key, key))
        if kwargs:
            try:
                return template.format(**kwargs)
            except KeyError:
                return template
        return template

    def list_supported_languages(self) -> Dict[str, str]:
        return {
            "en": "English",
            "de": "Deutsch",
            "fr": "Français",
            "es": "Español",
            "zh": "中文 (简体)",
            "ja": "日本語"
        }
