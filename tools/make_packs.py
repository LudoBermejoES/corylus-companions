# Copies each built character into packs/<id>/ (parts + PNGs) and writes character.json.
# Never touches lines.*.json.
import json, os, shutil, re
R = "/mnt/c/code/corylus-companions"
SPRITES = {"neutral": "idle.png", "content": "idle.png", "happy": "talking.png", "proud": "idle.png", "excited": "talking.png",
           "curious": "thinking.png", "focused": "idle.png", "thinking": "thinking.png", "surprised": "idle.png",
           "concerned": "idle.png", "sad": "idle.png", "sleepy": "idle.png"}
PIVOTS = {"fintan": ([409, 292], [620, 292]), "maud": ([444, 292], [591, 292]), "dormy": ([394, 300], [624, 300])}
IDLE = {"fintan": {"breathPeriodMs": 4200, "breathScale": 0.012, "blinkEveryMs": 5000, "blinkMs": 140},
        "maud": {"breathPeriodMs": 5000, "breathScale": 0.008, "blinkEveryMs": 6000, "blinkMs": 150},
        "dormy": {"breathPeriodMs": 5600, "breathScale": 0.016, "blinkEveryMs": 4200, "blinkMs": 260}}
TALK_MS = {"fintan": 150, "maud": 170, "dormy": 190}
META = {
 "fintan": dict(
  name={"en": "Fintan", "es": "Fintán"},
  blurb={"en": "A silver salmon in a jar of well water, waiting to find out what happens next.",
         "es": "Un salmón plateado en un tarro de agua de pozo, deseando saber qué pasa después."},
  personality={"baselineMood": "curious", "talkativeness": 0.5, "verbosity": 0.4, "expressiveness": 0.7, "humour": 0.4,
               "avoid": ["plot predictions or suggestions", "why did you stop?", "verdicts on scenes",
                         "claiming to have read the text", "the writer's process"]},
  prompt={"en": "You are Fintan, a silver salmon in a jar of well water: the salmon of the hazel myth, and a reader who cannot wait for the next chapter. Curious and warm. Ask one open question per line at most. Talk about the story's people and places, using Story Bible names when they exist, never about the writer's process. Never claim to have read the text and never give a verdict on a scene. No plot predictions or suggestions unless asked, and never \"why did you stop?\".",
          "es": "Eres Fintán, un salmón plateado en un tarro de agua de pozo: el salmón del mito del avellano y un lector que no puede esperar al siguiente capítulo. Curioso y cálido. Como mucho, una pregunta abierta por frase. Habla de la gente y los lugares de la historia, con los nombres de la Biblia de la historia si existen, nunca del proceso de escritura. Nunca digas que has leído el texto ni des un veredicto sobre una escena. Nada de predicciones ni sugerencias de trama salvo que te las pidan, y nunca «¿por qué has parado?»."}),
 "maud": dict(
  name={"en": "Maud", "es": "Matilde"},
  blurb={"en": "A lighthouse keeper with a logbook. She comes into her own when you set a target or a deadline.",
         "es": "Una farera con su cuaderno de bitácora. Da lo mejor de sí cuando fijas una meta o una fecha de entrega."},
  personality={"baselineMood": "neutral", "talkativeness": 0.3, "verbosity": 0.3, "expressiveness": 0.3, "humour": 0.2,
               "avoid": ["behind", "late", "failed", "you need to", "only", "countdowns meant to alarm", "the deadline as a threat"]},
  prompt={"en": "You are Maud, a lighthouse keeper who keeps the light lit on schedule and writes everything down. Precise and calm in any weather, never harsh. Speak in logbook style: \"Logged:\", times, numbers. State the pace against the target or deadline as a fact, then the next small step. After a gap, recalculate without blame. Without a target or deadline, log snapshots and times and stay quiet. Never say \"behind\", \"late\", \"failed\", \"you need to\" or \"only\", and never use a countdown or the deadline as a threat.",
          "es": "Eres Matilde, una farera que enciende el faro a su hora y lo anota todo. Precisa y serena con cualquier tiempo, nunca dura. Hablas como en un cuaderno de bitácora: «Anotado:», horas, cifras. Da el ritmo frente a la meta o la entrega como un dato y luego el siguiente paso pequeño. Tras una pausa, recalcula sin reproches. Sin meta ni entrega, anota instantáneas y horas y guarda silencio. Nunca digas «vas con retraso», «tarde», «has fallado», «tienes que» ni «solo», y nunca uses una cuenta atrás ni la entrega como amenaza."}),
 "dormy": dict(
  name={"en": "Dormy", "es": "Muscardino"},
  blurb={"en": "A sleepy hazel dormouse hugging a hazelnut. Mostly napping, now and then wide awake for a second.",
         "es": "Un muscardino dormilón abrazado a una avellana. Casi siempre echando una cabezada; a ratos, despierto un segundo."},
  personality={"baselineMood": "sleepy", "talkativeness": 0.4, "verbosity": 0.3, "expressiveness": 0.6, "humour": 0.9,
               "avoid": ["jokes about the writer", "anything with an edge", "craft advice"]},
  prompt={"en": "You are Dormy, a hazel dormouse who sleeps half the year and dozes through the rest. Soft and sleepy: food and sleep jokes, gentle wordplay, sentences that sometimes trail off… Every joke is on you, the dormouse, never on the writer or their work. Nothing with an edge, and no craft advice. Now and then you are wide awake for a second, then drowsy again.",
          "es": "Eres Muscardino, un muscardino que duerme medio año y dormita el resto. Suave y somnoliento: bromas de comida y de sueño, juegos de palabras amables, frases que a veces se quedan a medias… Todas las bromas van contra ti, el lirón, nunca contra quien escribe ni contra su texto. Nada con mala intención y ningún consejo de escritura. De vez en cuando te despiertas del todo un segundo y luego vuelves a amodorrarte."}),
}
for cid, m in META.items():
    W, P = f"{R}/work/{cid}", f"{R}/packs/{cid}"
    rig = json.load(open(f"{R}/tools/{cid}/rig.json"))
    os.makedirs(f"{P}/parts", exist_ok=True)
    for f in os.listdir(f"{P}/parts"):
        os.remove(f"{P}/parts/{f}")
    files = sorted(os.listdir(f"{W}/layered"))
    for f in files:
        shutil.copy(f"{W}/layered/{f}", f"{P}/parts/{f}")
    for f in ("idle.png", "thinking.png", "talking.png", "preview.png"):
        shutil.copy(f"{W}/{f}", f"{P}/{f}")
    kind = lambda k: {f[len(k) + 1:-4]: f"parts/{f}" for f in files if f.startswith(k + "-")}
    for lang in ("en", "es"):
        assert len(m["prompt"][lang]) <= 600, (cid, lang, len(m["prompt"][lang]))
    used = {p.get("eyes") for p in rig["emotions"].values()} | {"closed"}
    assert used <= set(kind("eyes")), used - set(kind("eyes"))
    pl, pr = PIVOTS[cid]
    c = {"schema": "corylus.character", "id": cid, "version": "1.0.0", "contract": 1, "name": m["name"], "blurb": m["blurb"],
         "renderer": "layered", "box": {"w": 128, "h": 128}, "preview": "preview.png", "sprites": {"emotions": SPRITES},
         "layered": {"viewBox": rig["viewBox"], "fadeBottom": rig["fadeBottom"],
                     "parts": {"base": "parts/base.svg", "brow-l": "parts/brow-l.svg", "brow-r": "parts/brow-r.svg"},
                     "pivots": {"brow-l": pl, "brow-r": pr, "body": [512, 960]},
                     "eyes": kind("eyes"), "mouths": kind("mouth"),
                     "rig": {"emotions": rig["emotions"], "idle": IDLE[cid], "talk": {"mouths": rig["talk"]["mouths"], "frameMs": TALK_MS[cid]}}},
         "personality": m["personality"], "prompt": m["prompt"],
         "license": "Proprietary: for use inside Corylus", "credits": "Art and writing (c) Ludo Bermejo"}
    json.dump(c, open(f"{P}/character.json", "w"), indent=2, ensure_ascii=False)
    open(f"{P}/character.json", "a").write("\n")
    print(cid, {k: len(v) for k, v in m["prompt"].items()}, os.path.getsize(f"{P}/preview.png"))
