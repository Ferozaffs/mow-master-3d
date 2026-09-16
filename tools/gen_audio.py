"""Synthesizes game audio (music loop, mower engine, sfx) as WAVs."""
import numpy as np, os

SR = 44100
OUT = os.path.join(os.path.dirname(__file__), "wav")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)
from numpy.fft import rfft, irfft, rfftfreq

def save(name, data, peak=0.95):
    data = np.asarray(data, dtype=np.float64)
    m = np.max(np.abs(data)) or 1.0
    data = data / m * peak
    pcm = (data * 32767).astype(np.int16)
    import wave
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(name, round(len(data) / SR, 2), "s")

def env(n, a=0.005, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / d)

def pluck(freq, dur, vol=1.0, damp=0.9965):
    """Karplus-Strong string pluck — warm guitar/ukulele sound."""
    n = int(SR * dur); N = max(2, int(SR / freq))
    buf = rng.uniform(-1, 1, N)
    out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % N]
        buf[i % N] = damp * 0.5 * (buf[i % N] + buf[(i + 1) % N])
    return out * vol * env(n, a=0.002, d=dur * 0.9)

def whistle(freq, dur, vol=1.0, vib=5.2, vibd=0.007):
    n = int(SR * dur); t = np.arange(n) / SR
    f = freq * (1 + vibd * np.sin(2 * np.pi * vib * t) + 0.004 * np.sin(2 * np.pi * 0.9 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)
    a = np.minimum(1, t / 0.05)
    r = np.minimum(1, (t[-1] - t) / 0.18)
    return s * a * r * vol

def piano(freq, dur, vol=1.0):
    """Piano-like additive tone: hammer attack, per-partial decay, soft inharmonicity."""
    n = int(SR * dur); t = np.arange(n) / SR
    out = np.zeros(n)
    r11 = np.random.RandomState(11)
    for k in range(1, 9):
        f = freq * (k + 0.0007 * k * k) * (1 + 0.0015 * r11.uniform(-1, 1))
        # higher partials decay faster, like real piano strings
        d = dur * 0.85 / (1 + 0.55 * (k - 1))
        a = np.minimum(1, t / 0.004) * np.exp(-t / d)
        out += 0.85 * (1.0 / k ** 1.6) * np.sin(2 * np.pi * f * t) * a
    out += 0.04 * np.exp(-t / 0.03) * rng.uniform(-1, 1, n)  # hammer thud
    return out * vol

def sine(freq, dur, vol=1.0, slide_to=None, a=0.005, d=0.3):
    n = int(SR * dur); t = np.arange(n) / SR
    f = freq if slide_to is None else np.linspace(freq, slide_to, n)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * env(n, a=a, d=d) * vol

def noise(dur, vol=1.0):
    return rng.uniform(-1, 1, int(SR * dur)) * vol

def band(sig, lo, hi, soft=32):
    F = rfftfreq(len(sig), 1 / SR)
    m = ((F >= lo) & (F <= hi)).astype(float)
    m = np.convolve(m, np.hanning(soft) / np.hanning(soft).sum(), "same")[:len(m)]
    return irfft(rfft(sig) * m, len(sig))

def lp(sig, cut):
    return band(sig, 0, cut)

# ---------------- Music: 16-bar seamless waltz loop ----------------
BPM = 122; BEAT = 60 / BPM; BAR = 3 * BEAT; BARS = 16
LEN = BAR * BARS
music = np.zeros(int(len * SR) if False else int(LEN * SR) + SR * 3)  # extra tail folds back for a seamless loop

CH = {
    "C":  dict(root=130.81, chord=[261.63, 329.63, 392.00, 523.25], mel=[880.00, 1046.50, 783.99, 932.33, 659.26, 587.33]),
    "G":  dict(root=98.00,  chord=[196.00, 293.66, 392.00, 493.88], mel=[783.99, 987.77, 932.33, 880.00, 783.99, 659.26]),
    "Am": dict(root=110.00, chord=[220.00, 261.63, 329.63, 440.00], mel=[659.26, 880.00, 783.99, 698.46, 659.26, 523.25]),
    "F":  dict(root=87.31,  chord=[174.61, 261.63, 349.23, 440.00], mel=[698.46, 880.00, 783.99, 698.46, 659.26, 523.25]),
}
prog = ["C", "C", "G", "G", "Am", "Am", "F", "F", "C", "C", "G", "G", "Am", "F", "G", "C"]
mel_line = [0, 1, 2, None, 3, 2,
            4, None, 3, 2, 1, None,
            0, 2, 4, None, 3, None,
            5, 4, 3, None, 2, None,
            0, 1, 2, None, 4, None,
            3, 5, 2, None, 1, None,
            4, 2, 3, None, 0, None,
            5, None, 4, 3, 2, None]
mi = 0

def add(sig, at):
    i = int(at * SR)
    e = min(len(music), i + len(sig))
    music[i:e] += sig[:e - i]

for b in range(BARS):
    ch = CH[prog[b]]
    t0 = b * BAR
    # deep bass root on beat 1 (piano low register + sub octave)
    add(piano(ch["root"], 1.1, 0.9), t0)
    add(piano(ch["root"] / 2, 1.3, 0.6), t0 + 0.005)
    # broken piano chords on beats 2 & 3 + high octave accent on beat 3
    for beat in (1, 2):
        for k, f in enumerate(ch["chord"]):
            add(piano(f, 0.7, 0.4), t0 + beat * BEAT + k * 0.014)
    add(piano(ch["chord"][0] * 2, 0.55, 0.28), t0 + 2 * BEAT + 0.06)
    # melody on a piano voice
    idx = mel_line[mi]; mi += 1
    if idx is not None:
        add(piano(ch["mel"][idx], BEAT * 1.75, 0.55), t0 + 0.02)
    idx2 = mel_line[mi]; mi += 1
    if idx2 is not None:
        add(piano(ch["mel"][idx2], BEAT * 1.1, 0.4), t0 + BEAT * 2.02)
    # shaker: soft ticks on every beat, accented on 1
    for beat in range(3):
        nn = int(SR * 0.09)
        tick = band(rng.uniform(-1, 1, nn), 3800, 11000, soft=16) * env(nn, a=0.001, d=0.02)
        add(tick * (0.5 if beat == 0 else 0.3), t0 + beat * BEAT)

# fold the tail back so the loop is seamless
tail = music[int(LEN * SR):]
music_fold = music[:int(LEN * SR)]
music_fold[:len(tail)] += tail
save("music", music_fold)

# ---------------- Mower engine: 3s seamless loop ----------------
n = int(SR * 3.0)
t = np.arange(n) / SR
eng = np.zeros(n)
base = 52  # 156 cycles in 3s; every modulator below also completes integer cycles
for h, amp in [(1, 1.0), (2, 0.55), (3, 0.32), (4, 0.22), (5, 0.12), (6, 0.08)]:
    f = base * h * (1 + 0.035 * np.sin(2 * np.pi * 26 * t) + 0.02 * np.sin(2 * np.pi * 13 * t))
    eng += amp * np.sin(2 * np.pi * np.cumsum(f) / SR)
chop = (1 - np.abs(((t * 40) % 1) * 2 - 1)) ** 6  # 40*3 = 120 cycles
eng += 1.3 * chop * (np.sin(2 * np.pi * 205 * t) * 0.5 + rng.uniform(-1, 1, n) * 0.4)
F = rfftfreq(n, 1 / SR)
m = ((F >= 300) & (F <= 2400)).astype(float)
his = irfft(rfft(rng.uniform(-1, 1, n)) * (0.35 + 0.25 * np.sin(2 * np.pi * 6 * t))[:1] * m, n)
eng += 0.32 * his
eng += 0.25 * np.sin(2 * np.pi * base / 2 * t)
save("engine", eng, peak=0.9)

# ---------------- One-shot SFX ----------------
# gnome grumble "hm... HRM!"
g = np.zeros(int(SR * 1.1))
g[:int(SR*0.3)] += sine(118, 0.3, 1.0, slide_to=95, d=0.14) + lp(noise(0.3, 0.35), 900)
g[int(SR*0.46):int(SR*0.46)+int(SR*0.4)] += sine(152, 0.4, 1.15, slide_to=86, d=0.11)
g[int(SR*0.46):int(SR*0.46)+int(SR*0.4)] += lp(noise(0.4, 0.4), 1150)
save("gnome", g)

# double chicken cluck "bok-bok"
c = np.zeros(int(SR * 0.5))
c[:int(SR*0.16)] += sine(680, 0.16, 1.0, slide_to=420, d=0.05) + lp(noise(0.16, 0.4), 2600)
at = int(SR * 0.18)
seg = sine(640, 0.14, 0.9, slide_to=410, d=0.05) + lp(noise(0.14, 0.35), 2400)
c[at:at + len(seg)] += seg
save("cluck", c)

# panicked squawk
nn = int(SR * 0.65)
t2 = np.arange(nn) / SR
f = np.linspace(1300, 300, nn) * (1 + 0.06 * np.sin(2 * np.pi * 42 * t2))
ph = 2 * np.pi * np.cumsum(f) / SR
sq = np.tanh(3.0 * np.sin(ph) + 0.4 * np.sin(2 * ph)) * env(nn, a=0.004, d=0.2)
s = np.zeros(int(SR * 0.7))
s[:nn] += sq
save("squawk", s)

# bat hit: crack + wooden thock + springy boing + squeal
h = np.zeros(int(SR * 1.5))
crack = noise(0.1, 1.0) * env(int(SR * 0.1), a=0.001, d=0.014)
h[:len(crack)] += crack
for f0, d0, amp in [(265, 0.12, 0.85), (195, 0.18, 0.75), (545, 0.08, 0.5), (1250, 0.05, 0.4)]:
    seg = sine(f0, d0, amp, d=d0 * 0.45, a=0.001)
    h[:len(seg)] += seg
nn = int(SR * 0.6)
t2 = np.arange(nn) / SR
fb = 250 * np.exp(-t2 * 3.2) + np.abs(np.sin(2 * np.pi * 23 * t2)) * 26
ph = 2 * np.pi * np.cumsum(fb) / SR
boing = np.sin(ph) * env(nn, a=0.002, d=0.12) * 0.85
h[int(SR*0.05):int(SR*0.05)+nn] += boing
nn2 = int(SR * 0.35)
sq2 = sine(1000, 0.35, 0.4, slide_to=280, d=0.12)
h[int(SR*0.13):int(SR*0.13)+nn2] += sq2
save("hit", np.clip(h, -1, 1))

# bat swing whoosh
nn = int(SR * 0.42)
w = rng.uniform(-1, 1, nn)
W = rfft(w); F2 = rfftfreq(nn, 1 / SR)
sweep_line = np.interp(np.linspace(0, 1, len(F2)), [0, 1], [350, 3400])
mask = np.exp(-((F2 / sweep_line - 1) ** 2) / 0.4)
w = irfft(W * mask, nn)
w *= env(nn, a=0.09, d=0.13)
save("swing", w)

# grass footstep
nn = int(SR * 0.13)
st = band(rng.uniform(-1, 1, nn), 150, 1500) * env(nn, a=0.002, d=0.028)
save("step", st)
