		ASCII art generator

Convert your image (.png/.jpg/.jpeg/.webp) to a text-image (.txt)

How to use: 1) Make sure you have installed all necessary python libraries - see below
	    2) Start the program with: uv run ascii-art
	    3) Click "Select picture" to choose an image from your PC, or paste an image URL
	       into the field below - these two inputs are mutually exclusive, so using one
	       clears the other. A pasted URL is checked in the background and marked
	       "Valid URL" or "Not valid URL" as you type.
	    4) Choose your settings - whether to also save the result as a .txt file, and the
	       output resolution. Original size is preselected; you can also pick the fixed
	       SMS size or enter a custom width/height in symbols.
	    5) Click "Generate"
	    6) In the result window, click "Copy" to copy the text-image to the clipboard,
	       "New image" to generate another one (the window reopens in the same spot),
	       or "Exit" to close the program. If the result is too large to fit on screen,
	       scrollbars let you see all of it.

You can also switch between Light/Dark theme and English/Czech language at the bottom
of the main window at any time.

Tips: You can achieve the best text image by setting the resolution as close as possible to the original resolution of the image
      Coloured images may not be perfect, the best text-image comes from monochromic images
      Very large images may not fully fit the result window at once, so use the scrollbars, or copy/save the text-image to a .txt file


Setup: This project uses uv (https://docs.astral.sh/uv/) to manage the Python environment and dependencies.
		  1) Install uv - see https://docs.astral.sh/uv/getting-started/installation/
		  2) From the repository root, run:
       		uv sync
		  3) Start the program with:
       		uv run ascii-art

Python libraries used by the project:
		  - Customtkinter - https://pypi.org/project/customtkinter
		  - Pillow - https://pypi.org/project/Pillow
		  - Requests - https://pypi.org/project/requests

created by: MichalS16

--------------------------------------------------------------------------------------------------------------------------------------------------------

		ASCII art generátor

Převeďte svůj obrázek (.png/.jpg/.jpeg/.webp) na textový obrázek (.txt)

Jak používat: 1) Ujistěte se, že máte nainstalovány všechny potřebné python knihovny – viz. níže
	      2) Spusťte program příkazem: uv run ascii-art
	      3) Klikněte na "Vyberte obrázek" a zvolte obrázek z vašeho PC, nebo vložte URL
	         obrázku do pole níže - tyto dva vstupy se vzájemně vylučují, takže použití
	         jednoho vymaže druhý. Vložená URL se na pozadí ověřuje a při psaní se
	         zobrazí "Platná URL" nebo "Neplatná URL".
	      4) Zvolte si nastavení - zda výsledek uložit i jako .txt soubor a výstupní
	         rozlišení. Přednastavena je původní velikost; můžete také zvolit pevnou
	         SMS velikost nebo zadat vlastní šířku/výšku v symbolech.
	      5) Klikněte na "Generovat"
	      6) Ve výsledkovém okně klikněte na "Kopírovat" pro zkopírování textového
	         obrázku do schránky, na "Nový obrázek" pro vygenerování dalšího (okno se
	         znovu otevře na stejném místě), nebo na "Odejít" pro ukončení programu.
	         Pokud se výsledek nevejde celý na obrazovku, posuvníky umožňují zobrazit
	         zbytek.

Motiv (Light/Dark) a jazyk (EN/CZ) lze kdykoliv přepnout dole v hlavním okně.

Typy: Nejlepšího textového obrázku dosáhnete nastavením rozlišení co nejblíže původnímu rozlišení obrázku
      Barevné obrázky nemusí být dokonalé, nejlepší textový obrázek vznikne z monochromatických obrázků
      Velmi velké obrázky se nemusí celé vejít do výsledkového okna najednou, použijte proto posuvníky, nebo zkopírujte/uložte textový obrázek do souboru .txt


Instalace: Tento projekt používá uv (https://docs.astral.sh/uv/) pro správu Python prostředí a závislostí.
		  1) Nainstalujte uv - viz https://docs.astral.sh/uv/getting-started/installation/
		  2) V kořenovém adresáři repozitáře spusťte:
       		uv sync
		  3) Program spustíte příkazem:
       		uv run ascii-art

Knihovny Pythonu použité v projektu:
		  - Customtkinter - https://pypi.org/project/customtkinter
		  - Pillow - https://pypi.org/project/Pillow
		  - Requests - https://pypi.org/project/requests

vytvořil: MichalS16
