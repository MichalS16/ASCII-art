"""
User interface section of ASCII_art program

How to ASCII generator: Please run "main.py" in current folder

created by: Michal S.
"""

# import generator of ASCII
from ascii_generator import *

# import modules
from tkinter import *
from tkinter import filedialog
import customtkinter
import subprocess
import requests

# language words
languageENG=["ASCII-art generator", "ASCII generator", "Select picture", "Choose one option", "Insert URL of image", "Settings:", "Download in .txt file", "Select a resolution", "SMS - 12x12 - symbols", "Original size", "Custom size", "Generate", "Theme", "About", "CZE", "Open image file", "Type in a resolution: widthxheight\n(in text symbols)", "Please respect the resolution format:\nwidthxheight\nE.g. 500x400", "Error occurred!", "Your URL is not valid!\nonly .png/.jpg/.jpeg\nrepair URL here or close window", "Please choose one option of an image input", " - symbols", "ASCII-art generator - result", "You can edit the text as you like.\nIf the text-image is displayed incorrectly, copy or save to .txt ", "New image", "Copy", "Exit", "Please select the resolution of the generated image"]
languageCZK=["ASCII-art generátor", "ASCII generátor", "Vyberte obrázek", "Vyberte jednu možnost", "Vložte URL obrázku", "Nastavení:", "Stáhnout v .txt souboru", "Vyberte rozlišení", "SMS - 12x12 - symbolů", "Původní velikost", "Vlastní velikost", "Generovat", "Pozadí", "Nápověda", "ENG", "Otevřete soubor s obrázkem", "Napište rozlišení: šířkaxvýška\n(v textových symbolech)", "Prosím respektujte formát rozlišení:\nšířkaxvýška\nnapř. 500x400", "Vyskytla se chyba!", "Vaše URL je neplatná!\npouze .png/.jpg/.jpeg\nopravte URL zde nebo zavřete okno", "Prosím zvolte jednu možnost vložení Vašeho obrázku", " - symbolů", "ASCII-art generátor - výsledek", "Můžete upravit text podle libosti\nPokud se textový obrázek zobrazuje nesprávně zkopírujte nebo uložte do .txt ", "Nový obrázek", "Kopírovat", "Odejít", "Prosím vyberte rozlišení vygenerovaného obrázku"]

# define global variables
pc_image_path=""
theme=""
downstate=""
size=""

# define mainwindow, output variables - downstate, image_path, size
def mainwindow():
    global ui1

    # function to output path to user image, output - image_path
    def generate(condition=""):
        global image_path
        global pc_image_path
        
        if (entry_URL.get()!="" and pc_image_path!="") or (entry_URL.get()=="" and pc_image_path=="") and size!="":
            popwindow=customtkinter.CTkToplevel()
            popwindow.geometry("475x50")
            popwindow.title(languageENG[18])
            popwindow.resizable(0,0)
            label=customtkinter.CTkLabel(popwindow, text=languageENG[20], text_color=("black","snow3"), text_font=("Verdana","11","bold"))
            label.pack(pady=10)
        
        if entry_URL.get()!="" and pc_image_path=="" and size!="":
            image_formats=("image/png", "image/jpeg", "image/jpg")

            if condition=="error":
                badurl=customtkinter.CTkInputDialog(master=frame, text=languageENG[19], title=languageENG[18])
                entryurl=badurl.get_input()
            else:
                entryurl=entry_URL.get()

            try:
                check=requests.head(entryurl)

                if check.headers["content-type"] not in image_formats:
                    generate("error")
                else:
                    image_path=requests.get(entryurl)
                    filename="Results-Výsledky/"+''.join(entryurl.split("/")[-1])
                    open(filename, "wb").write(image_path.content)
                    secondwindow(generator(downstate, filename, size))

                    if rerun==TRUE:
                        mainwindow()

            except:
                if entryurl!=None:
                    generate("error")
        
        if pc_image_path!="" and entry_URL.get()=="" and size!="":
            image_path=pc_image_path
            secondwindow(generator(downstate, image_path, size))

            if rerun==TRUE:
                mainwindow()
        
        if size=="":
            popwindow=customtkinter.CTkToplevel()
            popwindow.geometry("475x50")
            popwindow.title(languageENG[18])
            popwindow.resizable(0,0)
            label=customtkinter.CTkLabel(popwindow, text=languageENG[27], text_color=("black","snow3"), text_font=("Verdana","11","bold"))
            label.pack(pady=10)
        else:
            entry_URL.delete(0,"end")
            pc_image_path=""
            button_select.configure(fg_color="steelblue3")

    # function to determine download of text file with generated text-image, output - downstate
    def downloadstate():
        global downstate

        downstate=checkbox_download.get()

    # function to determine a size of generate image text, output - size
    def menu(condition):
        global size

        if condition=="error":
            custom=customtkinter.CTkInputDialog(master=None, text=languageENG[17], title=languageENG[18])
            try:
                size=[eval(i) for i in custom.get_input().split("x")]
                optionmenu.configure(fg_color="green")
                optionmenu.set(str(size[0])+"x"+str(size[1])+languageENG[21])
            except AttributeError:
                optionmenu.configure(fg_color="steelblue3")
                pass
            except:
                menu("error")
        
        if condition==languageENG[8]:
            size=[12, 12]
            optionmenu.configure(fg_color="green")
        
        if condition==languageENG[9]:
            size="original"
            optionmenu.configure(fg_color="green")
        
        if condition==languageENG[10]:
            optionmenu.configure(fg_color="steelblue3")
            custom=customtkinter.CTkInputDialog(master=None, text=languageENG[16], title=languageENG[7])
            try:
                size=[eval(i) for i in custom.get_input().split("x")]
                optionmenu.configure(fg_color="green")
                optionmenu.set(str(size[0])+"x"+str(size[1])+languageENG[21])
            except AttributeError:
                optionmenu.configure(fg_color="steelblue3")
                pass
            except:
                menu("error")
    
    # function to open ReadMe.txt in notepad
    def opentext():
        subprocess.Popen("notepad ReadME.txt")

    # function to change theme, turn_on=dark
    def changetheme():
        global theme

        if switch_theme.get()==1:
            customtkinter.set_appearance_mode("dark")
            theme="dark"
        else:
            customtkinter.set_appearance_mode("light")
            theme="light"

    # function to change language, turn_on=CZK
    def changelanguage():
        global languageENG
        global languageCZK

        if switch_language.get()==1:
            languageENG, languageCZK=languageCZK, languageENG
        if switch_language.get()==0:
            languageENG, languageCZK=languageCZK, languageENG
        
        if optionmenu.get()==languageCZK[7]:
            optionmenu.set(languageENG[7])
        elif optionmenu.get()==languageCZK[8]:
            optionmenu.set(languageENG[8])
        elif optionmenu.get()==languageCZK[9]:
            optionmenu.set(languageENG[9])
        elif optionmenu.get()==languageCZK[10]:
            optionmenu.set(languageENG[10])
        else:
            optionmenu.set(str(size[0])+" x "+str(size[1])+languageENG[21])
        
        ui1.title(languageENG[0])
        label_name1.configure(text=languageENG[1])
        button_select.configure(text=languageENG[2])
        label_name2.configure(text=languageENG[3])
        entry_URL.configure(placeholder_text=languageENG[4])
        label_name3.configure(text=languageENG[5])
        checkbox_download.configure(text=languageENG[6])
        optionmenu.configure(values=[languageENG[8],languageENG[9],languageENG[10]])
        button_generate.configure(text=languageENG[11])
        switch_theme.configure(text=languageENG[12])
        button_link.configure(text=languageENG[13])
        switch_language.configure(text=languageENG[14])

    # function to find path of image in PC
    def openfile():
        global pc_image_path
        
        pc_image_path=filedialog.askopenfilename(title=languageENG[15], filetypes=[("Image Files","*.jpg *.jpg *.png *.jpeg")])

        if pc_image_path!="":
            button_select.configure(fg_color="green")
        else:
            button_select.configure(fg_color="steelblue3")

    # set window size and title, default theme
    ui1=customtkinter.CTk()
    ui1.geometry("650x400")
    ui1.title(languageENG[0])
    ui1.resizable(0,0)

    # set frame "floating window"
    frame=customtkinter.CTkFrame(master=ui1, corner_radius=15, fg_color=("white","snow4"))
    frame.pack(padx=10, pady=10,ipadx=30,ipady=30)

    # set label name at top - "ASCII generator"
    label_name1=customtkinter.CTkLabel(master=frame, text=languageENG[1], text_color=("snow3","black"), text_font=("Verdana","40"))
    label_name1.grid(row=0, column=1, pady=10, columnspan=3,sticky="W")

    # set button to insert picture from PC
    button_select=customtkinter.CTkButton(master=frame, command=openfile, width=175, text=languageENG[2], text_font=("Verdana","15"), text_color=("white","black"), fg_color="steelblue3", hover_color=("snow3","snow2"))
    button_select.grid(row=1, column=2, pady=10, sticky="N")

    # set label name between insert - "Choose one option"
    label_name2=customtkinter.CTkLabel(master=frame, text=languageENG[3], text_color=("snow3","black"), text_font=("Verdana","11","bold"))
    label_name2.grid(row=2, column=2, sticky="N")

    # set line to entry URL of image 
    entry_URL=customtkinter.CTkEntry(master=frame, height=25, width=175, placeholder_text=languageENG[4], placeholder_text_color=("steelblue3","black"), text_color=("steelblue3","black"), fg_color=("white","snow4"), border_color="gray40")
    entry_URL.grid(row=3, column=2, pady=10, sticky="N")

    # set label for row with settings - "Setting"
    label_name3=customtkinter.CTkLabel(master=frame, text=languageENG[5], text_font=("Verdana","12","bold"), text_color=("snow3","black"))
    label_name3.grid(row=4, column=0, pady=20, columnspan=2, sticky="E")

    # set checkbox to download
    checkbox_download=customtkinter.CTkCheckBox(master=frame, command=downloadstate, text=languageENG[6], text_font=("Verdana","10","bold"), text_color=("snow3","black"), fg_color="steelblue3", border_color="gray40", hover_color="steelblue3")
    checkbox_download.grid(row=4, column=2,padx=30, pady=22, columnspan=2,sticky="W")

    # set menu to select size of output
    optionmenu=customtkinter.CTkOptionMenu(master=frame, command=menu, height=25, width=175, text_color=("white","black"), fg_color="steelblue3", button_color=("steelblue2"), button_hover_color=("snow3","snow2"), dropdown_color="steelblue3",dropdown_text_color=("white","black"), dropdown_hover_color=("snow3","snow2"), values=[languageENG[8], languageENG[9], languageENG[10]])
    optionmenu.grid(row=4, column=3, pady=22, columnspan=2, sticky="W")
    optionmenu.set(languageENG[7])

    # set button generate text form of image
    button_generate=customtkinter.CTkButton(master=frame, command=generate, width=200, text=languageENG[11], text_font=("Verdana","20","bold"), text_color=("white","black"), fg_color="steelblue3", hover_color=("snow3","snow2"))
    button_generate.grid(row=5, column=2, pady=10, sticky="N")

    # set switch to change light or dark theme
    switch_theme=customtkinter.CTkSwitch(master=frame, command=changetheme, text=languageENG[12], text_font=("Verdana","9","bold"), text_color=("snow3","black"), fg_color="snow3", button_color="steelblue3", button_hover_color="steelblue3")
    switch_theme.grid(row=6, column=0, padx=10, pady=15, sticky="S")

    # set button "About" to open ReadME.txt
    button_link=customtkinter.CTkButton(master=frame, command=opentext, width=0, height=0, text=languageENG[13], text_font=("Verdana","8","bold"), text_color=("snow3","black"), fg_color=("white","snow4"), hover=False)
    button_link.grid(row=6, column=2, pady=8, sticky="S")

    # set switch to change language CZK or ENG
    switch_language=customtkinter.CTkSwitch(master=frame, command=changelanguage, text=languageENG[14], text_font=("Verdana","9","bold"), text_color=("snow3","black"), fg_color=("snow3","gray40"), button_color="steelblue3", button_hover_color="steelblue3")
    switch_language.grid(row=6, column=4, pady=15, sticky="W")

    # logic function to identify theme mode
    if theme=="light":
        customtkinter.set_appearance_mode("light")
        switch_theme.deselect()
    else:
        customtkinter.set_appearance_mode("dark")
        switch_theme.select()
    
    # run window
    ui1.mainloop()

# define secondwindow, input variables - textimage, size
def secondwindow(textimagedata):
    global rerun
    rerun=False

    # function to close result widnow and generate new image
    def newimage():
        global rerun
        rerun=True
        ui2.destroy()
        ui1.destroy()

    # function to copy text-image to clipboard
    def copy():
        ui2.clipboard_clear()
        ui2.clipboard_append(text.get("1.0", "end-1c"))
    
    # function to exit whole program
    def exit():
        ui2.destroy()
        ui1.destroy()

    # function to determine minimum and maximum width of text widget and window overalll
    if textimagedata[1]<61:
        textimagedata[1]=60
    if textimagedata[1]>200:
        textimagedata[1]=200
    if textimagedata[2]<6:
        textimagedata[2]=5
    if textimagedata[2]>50:
        textimagedata[2]=50
    winwidth=textimagedata[1]*8+298
    winheight=textimagedata[2]*16+132
    winsize=str(winwidth)+"x"+str(winheight)

    # function to change text widget background color from mainwindow
    if theme=="dark":
        themecolor="snow3"
    if theme=="light":
        themecolor="snow2"
    
    # set window size and title, default theme
    ui2=customtkinter.CTk()
    ui2.geometry(winsize)
    ui2.title(languageENG[22])
    ui2.resizable(1,1)

    # set frame "floating window"
    frame=customtkinter.CTkFrame(master=ui2, corner_radius=15, fg_color=("white","snow4"))
    frame.pack(padx=10, pady=10,ipadx=800,ipady=450)

    # set label name at top - "possible to be edited"
    label_name4=customtkinter.CTkLabel(master=frame, text=languageENG[23], text_color=("snow3","black"), text_font=("Verdana","11","bold"))
    label_name4.grid(row=0, column=1, pady=10)

    # set text frame to display generated text-image
    text=Text(frame, width=textimagedata[1], height=textimagedata[2], bg=themecolor, bd=0)
    text.tag_configure("center", justify='center')
    text.insert("1.0", textimagedata[0])
    text.tag_add("center", "1.0", "end")
    text.grid(row=1, column=1)

    # set labels to create space in sides
    label_name5=customtkinter.CTkLabel(master=frame, text="")
    label_name5.grid(row=1, column=0)
    label_name6=customtkinter.CTkLabel(master=frame, text="")
    label_name6.grid(row=1, column=2)

    # set button to new image
    button_generate=customtkinter.CTkButton(master=frame, command=newimage, width=20, text=languageENG[24], text_font=("Verdana","15"), text_color=("white","black"), fg_color="steelblue3", hover_color=("snow3","snow2"))
    button_generate.grid(row=2, column=1, pady=10, sticky="NW")

    # set button to Copy
    button_generate=customtkinter.CTkButton(master=frame, command=copy, width=20, text=languageENG[25], text_font=("Verdana","15"), text_color=("white","black"), fg_color="steelblue3", hover_color=("snow3","snow2"))
    button_generate.grid(row=2, column=1, pady=10, sticky="N")

    # set button exit
    button_generate=customtkinter.CTkButton(master=frame, command=exit, width=20, text=languageENG[26], text_font=("Verdana","15"), text_color=("white","black"), fg_color="steelblue3", hover_color=("snow3","snow2"))
    button_generate.grid(row=2, column=1, pady=10, sticky="NE")

    # run window
    ui2.mainloop()

# define function to run mainwindow
def run():
    mainwindow()