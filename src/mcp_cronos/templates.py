"""
Template e modelli dati per il diario.

Definisce le strutture dati per le entry del diario e i template
per la generazione del markdown.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from mcp_cronos.config import load_config
from mcp_cronos.utils.dates import get_standup_title


@dataclass
class Riferimento:
    """Rappresenta un riferimento (repository, branch, Jira, MR, etc.)."""

    tipo: str  # "repository", "branch", "jira", "gitlab_mr", etc.
    valore: str
    url: Optional[str] = None


@dataclass
class Entry:
    """
    Rappresenta una singola entry del diario di lavoro.

    Formato markdown risultante:
    ```
    ### {progetto} - {descrizione}

    {*-Richiesto da {richiesto_da}-* se presente}

    {paragrafo_intro}

    {contenuto}

    **Riferimenti:**
    - Repository: {repo}
    - Branch: `{branch}`
    - Jira: [{ticket}]({url})
    - GitLab MR: [MR !{numero}]({url})
    ```
    """

    progetto: str
    descrizione: str
    paragrafo_intro: str
    contenuto: str = ""
    richiesto_da: Optional[str] = None
    riferimenti: list[Riferimento] = field(default_factory=list)

    def to_markdown(self) -> str:
        """
        Converte l'entry in formato markdown.

        Returns:
            Stringa markdown formattata
        """
        config = load_config()
        lines = []

        # Header H3
        lines.append(f"### {self.progetto} - {self.descrizione}")
        lines.append("")

        # Requested-by line (optional), label localised via config.
        if self.richiesto_da:
            lines.append(f"*-{config.section_requested_by} {self.richiesto_da}-*")
            lines.append("")

        # Paragrafo introduttivo
        lines.append(self.paragrafo_intro)
        lines.append("")

        # Contenuto aggiuntivo
        if self.contenuto:
            lines.append(self.contenuto)
            lines.append("")

        # Riferimenti
        if self.riferimenti:
            lines.append(f"**{config.section_references}:**")
            for ref in self.riferimenti:
                if ref.url:
                    if ref.tipo.lower() == "branch":
                        lines.append(f"- {ref.tipo.title()}: `{ref.valore}`")
                    elif ref.tipo.lower() in ("jira", "gitlab_mr", "gitlab mr"):
                        lines.append(f"- {ref.tipo.title()}: [{ref.valore}]({ref.url})")
                    else:
                        lines.append(f"- {ref.tipo.title()}: [{ref.valore}]({ref.url})")
                else:
                    if ref.tipo.lower() == "branch":
                        lines.append(f"- {ref.tipo.title()}: `{ref.valore}`")
                    else:
                        lines.append(f"- {ref.tipo.title()}: {ref.valore}")

        return "\n".join(lines)


@dataclass
class DiarioGiornaliero:
    """
    Rappresenta il file del diario per un giorno specifico.

    Il titolo segue il formato "Per lo Stand-up {Giorno+1} {Mese} {Anno}".
    """

    data: date
    entries: list[Entry] = field(default_factory=list)
    bloccanti: str = "Nessuno"

    @property
    def titolo(self) -> str:
        """Genera il titolo per lo stand-up (giorno+1)."""
        return get_standup_title(self.data)

    def to_markdown(self) -> str:
        """
        Converte il diario giornaliero in formato markdown.

        Section names are taken from the active config so they reflect the
        configured language (e.g. "Cosa ho fatto ieri" for Italian, "What I
        did yesterday" for English).

        Returns:
            Stringa markdown completa
        """
        config = load_config()
        lines = []

        # Titolo H1
        lines.append(f"# {self.titolo}")
        lines.append("")

        # Entries section
        lines.append(f"## {config.section_entries}")
        lines.append("")

        # Entries con separatori
        for i, entry in enumerate(self.entries):
            lines.append(entry.to_markdown())
            lines.append("")
            lines.append("---")
            lines.append("")

        # Blockers section
        lines.append(f"## {config.section_blockers}")
        lines.append("")
        lines.append(self.bloccanti)
        lines.append("")

        return "\n".join(lines)

    def aggiungi_entry(self, entry: Entry) -> None:
        """
        Aggiunge una nuova entry al diario.

        Args:
            entry: Entry da aggiungere
        """
        self.entries.append(entry)

    def imposta_bloccanti(self, bloccanti: str) -> None:
        """
        Imposta il testo dei bloccanti.

        Args:
            bloccanti: Descrizione dei bloccanti o "Nessuno"
        """
        self.bloccanti = bloccanti if bloccanti else "Nessuno"


def crea_template_vuoto(data: date) -> str:
    """
    Crea un template vuoto per un nuovo file del diario.

    Section names and the blockers default are taken from the active config so
    that the generated template reflects the configured language.

    Args:
        data: Data del file

    Returns:
        Stringa markdown con il template vuoto
    """
    config = load_config()
    titolo = get_standup_title(data)
    return f"# {titolo}\n\n## {config.section_entries}\n\n## {config.section_blockers}\n\n{config.blockers_default}\n"
