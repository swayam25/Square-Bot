export type Track = { title: string; author: string; duration: number; artwork: string };

export const TRACKS: Track[] = [
    {
        title: "The Machine",
        author: "Reed Wonder & Aurora Olivas",
        duration: 192,
        artwork: "https://is1-ssl.mzstatic.com/image/thumb/Music126/v4/e3/4c/dd/e34cddab-815e-c82c-825c-5669b87796ce/cover.jpg/600x600bb.jpg",
    },
    {
        title: "End of Beginning",
        author: "Djo",
        duration: 159,
        artwork: "https://is1-ssl.mzstatic.com/image/thumb/Music221/v4/9d/58/bb/9d58bb3a-c6b5-4c3d-fbba-50872d2712f4/5056494917336.jpg/600x600bb.jpg",
    },
    {
        title: "The Night",
        author: "Eric Nam",
        duration: 221,
        artwork:
            "https://is1-ssl.mzstatic.com/image/thumb/Music126/v4/06/8c/bb/068cbb0f-8390-3a05-1112-80052999b949/8809603549204_Cover.jpg/600x600bb.jpg",
    },
    {
        title: "Harleys in Hawaii",
        author: "Katy Perry",
        duration: 185,
        artwork:
            "https://is1-ssl.mzstatic.com/image/thumb/Music114/v4/a1/09/bc/a109bc6a-21d2-53c5-248a-be19b20ba9da/20UMGIM53351.rgb.jpg/600x600bb.jpg",
    },
    {
        title: "Stay With Me",
        author: "CHANYEOL & Punch",
        duration: 192,
        artwork:
            "https://is1-ssl.mzstatic.com/image/thumb/Music125/v4/a9/0e/cf/a90ecfd1-0fe4-0fc9-10ab-a6ee62e127ba/8809534460814_Cover.jpg/600x600bb.jpg",
    },
];

export const time = (seconds: number) => `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(Math.floor(seconds) % 60).padStart(2, "0")}`;

class DemoPlayer {
    index = $state(0);
    elapsed = $state(120);
    playing = $state(true);
    filters = $state(["Bass Boost"]);
    readonly track = $derived(TRACKS[this.index]);
    readonly next = $derived(TRACKS[(this.index + 1) % TRACKS.length]);

    #viewers = 0;
    #timer: ReturnType<typeof setInterval> | undefined;

    attach() {
        if (this.#viewers++ === 0) this.#timer = setInterval(() => this.#tick(), 1000);
        return () => {
            if (--this.#viewers === 0) clearInterval(this.#timer);
        };
    }

    #tick() {
        if (!this.playing) return;
        if (this.elapsed + 1 >= this.track.duration) this.skip();
        else this.elapsed += 1;
    }

    toggle() {
        this.playing = !this.playing;
    }

    skip() {
        this.index = (this.index + 1) % TRACKS.length;
        this.elapsed = 0;
    }

    previous() {
        if (this.elapsed < 3) this.index = (this.index - 1 + TRACKS.length) % TRACKS.length;
        this.elapsed = 0;
    }

    toggleFilter(name: string) {
        this.filters = this.filters.includes(name) ? this.filters.filter((filter) => filter !== name) : [...this.filters, name];
    }

    seek(seconds: number) {
        this.elapsed = Math.max(0, Math.min(this.track.duration - 1, Math.round(seconds)));
    }
}

export const demo = new DemoPlayer();
