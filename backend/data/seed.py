"""
One-time ingestion script. Run: python -m backend.data.seed
Ingests all pre-prepared source files into Cognee Cloud.
"""
import asyncio
import httpx

API_BASE = "http://localhost:8000"

SOURCES = [
    # FEYNMAN
    {
        "figure_id": "feynman",
        "source_type": "text",
        # feynmanlectures.caltech.edu blocks scripted requests behind a Cloudflare
        # challenge, so this is ingested as text instead of fetched live.
        "content": (
            "Richard Feynman, The Feynman Lectures on Physics, Vol I, Chapter 1: Atoms in Motion, 1964:\n"
            "If, in some cataclysm, all of scientific knowledge were to be destroyed, and only one "
            "sentence passed on to the next generations of creatures, what statement would contain "
            "the most information in the fewest words? I believe it is the atomic hypothesis that "
            "all things are made of atoms - little particles that move around in perpetual motion, "
            "attracting each other when they are a little distance apart, but repelling upon being "
            "squeezed into one another. In that one sentence, there is an enormous amount of "
            "information about the world, if just a little imagination and thinking are applied."
        ),
        "metadata": {"title": "Feynman Lectures Vol I Ch1", "year": 1964, "doc_type": "lecture"},
    },
    {
        "figure_id": "feynman",
        "source_type": "url",
        "content": "https://www.nobelprize.org/prizes/physics/1965/feynman/lecture/",
        "metadata": {"title": "Nobel Lecture 1965", "year": 1965, "doc_type": "lecture"},
    },
    {
        "figure_id": "feynman",
        "source_type": "text",
        "content": (
            "Richard Feynman, Challenger Commission Testimony, 1986:\n"
            "For a successful technology, reality must take precedence over public relations, "
            "for Nature cannot be fooled. I found that the management of NASA did not "
            "communicate well with the engineers. The engineers were quite clear about "
            "the risks of the O-rings. The management chose not to hear those concerns. "
            "The decision to launch was taken at a level where the information was not "
            "fully available."
        ),
        "metadata": {"title": "Challenger Commission Testimony", "year": 1986, "doc_type": "testimony"},
    },
    {
        "figure_id": "feynman",
        "source_type": "text",
        "content": (
            "Richard Feynman, Omni Magazine Interview, 1979:\n"
            "I was born not knowing and have had only a little time to change that here and there. "
            "It is a great adventure to contemplate the universe, beyond man, to think of what it "
            "means without man, as it was for the great part of its long history and as it is in "
            "the great majority of places. When this objective view is finally attained, and the "
            "mystery and majesty of matter are fully appreciated, to then turn the objective eye "
            "back on man viewed as matter, to view life as part of this universal mystery of "
            "greatest depth, is to sense an experience which is very rare, and very exciting."
        ),
        "metadata": {"title": "Omni Magazine Interview", "year": 1979, "doc_type": "interview"},
    },
    {
        "figure_id": "feynman",
        "source_type": "text",
        "content": (
            "Richard Feynman on Education, from Surely You're Joking Mr. Feynman, 1985:\n"
            "The first principle is that you must not fool yourself - and you are the easiest "
            "person to fool. So you have to be very careful about that. After you've not fooled "
            "yourself, it's easy not to fool other scientists. You just have to be honest in a "
            "conventional way after that. I would like to add something that's not essential to "
            "the science, but something I kind of believe, which is that you should not fool the "
            "layman when you're talking as a scientist. I am not trying to tell you what to do "
            "about cheating on your wife, or fooling your mother about going to church, or "
            "anything like that. That's none of my business. But to not use your powers of "
            "persuasion in order to exaggerate how expert you are."
        ),
        "metadata": {"title": "Surely You're Joking Mr. Feynman", "year": 1985, "doc_type": "book"},
    },
    # TESLA
    {
        "figure_id": "tesla",
        "source_type": "text",
        # "My Inventions" isn't hosted as its own Project Gutenberg ebook (the
        # old gutenberg.org/files/13554 URL actually resolved to an unrelated
        # title), so this is ingested as text instead of scraped live.
        "content": (
            "Nikola Tesla, My Inventions, Electrical Experimenter, 1919, Chapter I: My Early Life:\n"
            "The progressive development of man is vitally dependent on invention. It is the most "
            "important product of his creative brain. Its ultimate purpose is the complete mastery "
            "of mind over the material world, the harnessing of the forces of nature to human needs. "
            "This is the difficult task of the inventor who is often misunderstood and unrewarded. "
            "But he finds ample compensation in the pleasing exercises of his powers and in the "
            "knowledge of being one of that exceptionally privileged class without whom the race "
            "would have long ago perished in the bitter struggle against pitiless elements."
        ),
        "metadata": {"title": "My Inventions", "year": 1919, "doc_type": "book"},
    },
    {
        "figure_id": "tesla",
        "source_type": "text",
        "content": (
            "Nikola Tesla, The Problem of Increasing Human Energy, Century Magazine, 1900:\n"
            "Of all the frictional resistances, the one that most retards human movement "
            "is ignorance, what Buddha called 'the greatest evil in the world.' "
            "The friction which results from ignorance can be reduced only by the spread "
            "of knowledge and the unification and harmonization of effort. "
            "There are resistances of a more material nature which also retard human movement. "
            "I have been long convinced that such a device can be produced, which, deriving "
            "energy from the environment, will more than supply the power consumed in its own "
            "operation and thus be capable of performing a net amount of external work."
        ),
        "metadata": {"title": "The Problem of Increasing Human Energy", "year": 1900, "doc_type": "article"},
    },
    {
        "figure_id": "tesla",
        "source_type": "text",
        "content": (
            "Nikola Tesla on Edison, from various interviews, 1890s-1910s:\n"
            "If he had a needle to find in a haystack he would not stop to reason where it was "
            "most likely to be, but would proceed at once, with the feverish diligence of a bee, "
            "to examine straw after straw until he found the object of his search. I was almost "
            "a sorry witness of such doings, knowing that a little theory and calculation would "
            "have saved him ninety per cent of his labor. Edison's method was inefficient in the "
            "extreme, for an immense ground had to be covered to get anything at all unless "
            "blind chance intervened and, at first, I was almost a sorry witness of his doings, "
            "knowing that just a little theory and calculation would have saved him ninety per "
            "cent of his labor."
        ),
        "metadata": {"title": "New York Times Interview on Edison", "year": 1931, "doc_type": "interview"},
    },
    {
        "figure_id": "tesla",
        "source_type": "text",
        "content": (
            "Nikola Tesla on Wireless Energy, 1904:\n"
            "The earth is 8,000 miles in diameter. The wireless waves to be used must "
            "accordingly have a length of not less than twenty kilometers. The capacity of "
            "the terrestrial globe will be such that, with twenty thousand horse-power, "
            "electric vibrations of the proper period can be transmitted through the earth "
            "to any point of its surface. The apparatus at Wardenclyffe has been designed "
            "to transmit electrical energy to any part of the globe. It is not a dream, it "
            "is a simple feat of scientific electrical engineering."
        ),
        "metadata": {"title": "The Transmission of Electrical Energy Without Wires", "year": 1904, "doc_type": "article"},
    },
]


async def seed():
    # Cognee ingests chunks one remote call at a time, so larger URL-sourced
    # documents (tens of chunks) need much more than a default 60s timeout.
    async with httpx.AsyncClient(timeout=300) as client:
        for i, source in enumerate(SOURCES):
            print(f"[{i+1}/{len(SOURCES)}] Ingesting: {source['metadata']['title']} ({source['figure_id']})")
            try:
                response = await client.post(f"{API_BASE}/ingest", json=source)
                response.raise_for_status()
                data = response.json()
                print(f"  OK nodes_created={data['nodes_created']}, topics={data['topics_detected']}")
            except Exception as e:
                print(f"  FAILED: {e}")

    print("\nSeeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())
