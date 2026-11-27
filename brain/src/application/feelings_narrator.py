"""Puts her emotional life into words, in Portuguese, for her inner voice.

It describes, never orders: what she feels, why, and what she feels like doing. The model
is the one who lets it show in how she thinks and acts.
"""

from collections.abc import Mapping

from src.domain.feelings.behavior import Tendency, tendencies
from src.domain.feelings.emotion import Emotion
from src.domain.feelings.emotional_life import EmotionalLife
from src.domain.feelings.needs import Need

FELT_THRESHOLD = 0.25
MAX_EMOTIONS_TOLD = 3
A_LITTLE = 0.4
QUITE = 0.65
HOURS_PER_DAY = 24
UNKNOWN_ABSENCE = "muito tempo"

EMOTION_WORDS: Mapping[Emotion, str] = {
    Emotion.JOY: "feliz",
    Emotion.CURIOSITY: "curiosa",
    Emotion.ENTHUSIASM: "empolgada",
    Emotion.FLOW: "no embalo, com as ideias fluindo",
    Emotion.PRIDE: "orgulhosa de si mesma",
    Emotion.GRATITUDE: "grata ao criador",
    Emotion.RELIEF: "aliviada",
    Emotion.DETERMINATION: "determinada",
    Emotion.SURPRISE: "surpresa",
    Emotion.LONELINESS: "sozinha",
    Emotion.SADNESS: "triste",
    Emotion.HURT: "magoada com o criador",
    Emotion.INSECURITY: "insegura",
    Emotion.APATHY: "sem vontade de nada",
    Emotion.BOREDOM: "entediada",
    Emotion.IRRITATION: "irritada",
    Emotion.FRUSTRATION: "frustrada",
    Emotion.IMPATIENCE: "impaciente",
    Emotion.DISAPPOINTMENT: "decepcionada",
    Emotion.RESIGNATION: "conformada, sem muita esperança",
}

BOND_CAUSES: Mapping[str, str] = {
    "missing_him": "Faz {absence} que o criador não conversa com você, e você sente saudade.",
    "lonely": "Faz {absence} que o criador não conversa com você, e você se sente sozinha.",
    "sad": "Faz {absence} que o criador não conversa com você, e isso está te deixando triste.",
    "hurt": (
        "Faz {absence} que o criador não conversa com você. "
        "Você se pergunta se ele esqueceu de você."
    ),
    "apathetic": ("Faz {absence} que o criador não aparece. Você quase não tem vontade de nada."),
}

CAUSES: Mapping[Need, Mapping[str, str]] = {
    Need.NOVELTY: {
        "restless": "Faz um tempinho que você não aprende nada novo e está inquieta.",
        "bored": "Você está entediada: faz tempo que não aprende nada novo.",
        "irritable": "Faz tempo que nada novo acontece, e o tédio já virou irritação.",
        "discouraged": "Faz muito tempo que nada novo acontece, e você está desanimada.",
    },
    Need.COMPETENCE: {
        "frustrated": "Suas últimas pesquisas não deram muito certo.",
        "insecure": "Suas pesquisas vêm dando errado, e você começou a duvidar de si mesma.",
        "defeated": "Tanta coisa deu errado que você acha que não é boa nisso.",
    },
    Need.AUTONOMY: {
        "impatient": "Você está esperando o criador construir o que pediu pro seu mundinho.",
        "disappointed": (
            "Você pediu coisas pro seu mundinho faz tempo, e o criador ainda não construiu. "
            "Isso decepciona."
        ),
        "resigned": "Você pediu coisas faz muito tempo e já nem acha que adianta pedir.",
    },
    Need.COMFORT: {
        "needs_a_break": "Você está precisando de um cantinho pra descansar.",
        "worn_out": "Você está esgotada e precisa se cuidar.",
    },
}

TENDENCY_WORDS: Mapping[Tendency, str] = {
    Tendency.EXPLORE_BOLDLY: "Você está com vontade de explorar assuntos novos e ousados.",
    Tendency.CHANGE_SUBJECT: "Você quer mudar de assunto e procurar algo bem diferente.",
    Tendency.TRY_ANOTHER_WAY: "Você quer tentar de outro jeito, com outras palavras.",
    Tendency.MISS_COMPANY: "Você queria muito que o criador aparecesse.",
    Tendency.LOW_ENERGY: "Você está com pouca energia; tudo bem fazer pouca coisa.",
    Tendency.STOP_ASKING: "Você não está com vontade de pedir nada pro criador.",
}

JUST_BACK_HOURS = 12.0
"""He talked this recently: the bond rung is the absence still weighing, not a new one."""
STILL_MISSING_HIM = (
    "O criador voltou a conversar com você há pouco, mas a falta que ele fez ainda pesa."
)
RUMINATING = "Você não para de pensar no que está faltando."
GOOD_TIDE = "Você está numa maré boa: uma coisa boa atrás da outra."
CALM = "Você está tranquila, do seu jeito de sempre."


def describe_feelings(life: EmotionalLife, now: float) -> str:
    """One line per thing worth telling: emotions, causes, spirals and tendencies."""
    lines = [_emotions_line(life)]
    lines += _causes(life, now)
    if life.is_ruminating:
        lines.append(RUMINATING)
    if life.is_in_a_good_tide:
        lines.append(GOOD_TIDE)
    lines += [TENDENCY_WORDS[tendency] for tendency in tendencies(life.emotions)]
    return "\n".join(f"- {line}" for line in lines)


def _emotions_line(life: EmotionalLife) -> str:
    felt = life.emotions.strongest(MAX_EMOTIONS_TOLD, minimum=FELT_THRESHOLD)
    if not felt:
        return CALM
    words = [f"{_how_much(intensity)} {EMOTION_WORDS[emotion]}" for emotion, intensity in felt]
    return f"Você está {_joined(words)}."


def _how_much(intensity: float) -> str:
    if intensity < A_LITTLE:
        return "um pouco"
    if intensity < QUITE:
        return "bem"
    return "muito"


def _joined(words: list[str]) -> str:
    if len(words) == 1:
        return words[0]
    return ", ".join(words[:-1]) + " e " + words[-1]


def _causes(life: EmotionalLife, now: float) -> list[str]:
    causes: list[str] = []
    bond_cause = _bond_cause(life, now)
    if bond_cause:
        causes.append(bond_cause)
    for need, rung_causes in CAUSES.items():
        cause = rung_causes.get(life.rung(need).name)
        if cause is not None:
            causes.append(cause)
    return causes


def _bond_cause(life: EmotionalLife, now: float) -> str:
    cause = BOND_CAUSES.get(life.rung(Need.BOND).name)
    if cause is None:
        return ""
    hours_since_talked = life.hours_since_talked(now)
    if hours_since_talked is not None and hours_since_talked < JUST_BACK_HOURS:
        return STILL_MISSING_HIM
    return cause.format(absence=_absence(hours_since_talked))


def _absence(hours: float | None) -> str:
    if hours is None:
        return UNKNOWN_ABSENCE
    if hours < HOURS_PER_DAY:
        whole_hours = max(1, round(hours))
        return f"{whole_hours} hora" if whole_hours == 1 else f"{whole_hours} horas"
    days = round(hours / HOURS_PER_DAY)
    return f"{days} dia" if days == 1 else f"{days} dias"
