"""
User interface section of ASCII_art program

How to use: please, run "main.py" in current folder

created by: Michal S.
"""

# import modules
import tkinter
from tkinter import filedialog
import customtkinter
from PIL import ImageTk,Image
import subprocess
import requests

# language words
language=["ASCII-art generator","ASCII generator","Select picture","(Choose one option)","Insert URL of image","Settings:","Download in .txt file","Select a resolution","SMS - 12x12 - size", "Origin size", "Custom (in pixels)","Generate","Theme","About","CZK","Open image file","Type in a resolution: widthxheight","Please respect the resolution format:\nwidthxheight\nE.g. 500x400","Error occurred!","Your URL is not valid!\nrepair URL here or close window"]
language1=["ASCII-art generátor","ASCII generátor","Vyberte obrázek","(Vyberte jednu možnost)","Vložte URL obrázku","Nastavení:","Stáhnout v .txt souboru","Vyberte rozlišení","SMS - 12x12 - velikost", "Původní velikost", "Vlastní (v pixelech)","Generovat","Pozadí","Nápověda","ENG","Otevřete soubor s obrázkem","Napište rozlišení: šířkaxvýška","Prosím respektujte formát rozlišení:\nšířkaxvýška\nnapř. 500x400","Vyskytla se chyba!","Vaše URL je neplatná!\nopravte URL zde nebo zavřete okno"]


# define mainwidow, variables - downstate, image_path, size
def mainwindow():

    # function to output path to user image
    def generate():
        if entry_URL.get()!="":
            entryurl=entry_URL.get()
            image_formats=("image/png", "image/jpeg", "image/jpg")
            check=requests.head(entryurl)
            if check.headers["content-type"] in image_formats:
                return True
            else:
                badurl=customtkinter.CTkInputDialog(master=frame, text=language[19], title=language[18])
                entryurl=badurl.get_input()
                generate()

    # function to determine download of text file
    def downloadstate():
        global downstate
        downstate=checkbox_download.get()
        if entry_URL.get()=="":
            print("hej")

    # function to determine a size of generate image text
    def menu(name):
        global size
        if name==language[8]:
            size=[12,12]
        elif name==language[9]:
            size=[0,0]
        elif name==language[10]:
            custom=customtkinter.CTkInputDialog(master=frame, text=language[16], title=language[7])
            try:
                size=[eval(i) for i in custom.get_input().split("x")]
            except:
                menu("error")
        elif name=="error":
            custom=customtkinter.CTkInputDialog(master=frame, text=language[17], title=language[18])
            try:
                size=[eval(i) for i in custom.get_input().split("x")]
            except:
                menu("error")
    
    # function to change theme, turn_on=dark
    def changetheme():
        if switch_theme.get()==1:
            customtkinter.set_appearance_mode("dark")
        else:
            customtkinter.set_appearance_mode("light")

    # function to change language, turn_on=CZK
    def changelanguage():
        global language
        global language1
        if switch_language.get()==1:
            language, language1=language1, language
        if switch_language.get()==0:
            language, language1=language1, language
        ui.title(language[0])
        label_name1.configure(text=language[1])
        button_select.configure(text=language[2])
        label_name2.configure(text=language[3])
        entry_URL.configure(placeholder_text=language[4])
        label_name3.configure(text=language[5])
        checkbox_download.configure(text=language[6])
        optionmenu.configure(values=[language[8],language[9],language[10]])
        optionmenu.set(language[7])
        button_generate.configure(text=language[11])
        switch_theme.configure(text=language[12])
        label_name4.configure(text=language[13])
        switch_language.configure(text=language[14])

    # function to find path to image in PC
    def openfile():
        global pc_image_path
        pc_image_path=filedialog.askopenfilename(title=language[15], filetypes=[("Image Files","*.jpg *.jpg *.png *.jpeg")])
        button_select.configure(fg_color="green")

    # set window size and title,default theme
    customtkinter.set_appearance_mode("System")
    ui=customtkinter.CTk()
    ui.geometry("650x400")
    ui.title(language[0])
    ui.resizable(0,0)

    # set frame "floating window"
    frame=customtkinter.CTkFrame(master=ui, corner_radius=15, fg_color=("white","snow4"))
    frame.pack(padx=10, pady=10,ipadx=30,ipady=30)

    # set label name at top - "ASCII generator"
    label_name1=customtkinter.CTkLabel(master=frame, text=language[1], text_color=("snow3","black"), text_font=("Verdana","40"))
    label_name1.grid(row=0, column=1, pady=10, columnspan=3,sticky="W")

    # set button to insert picture from PC
    button_select=customtkinter.CTkButton(master=frame, command=openfile, width=175, text=language[2], text_font=("Verdana","15"), text_color=("white","black"), hover_color=("snow3","snow2"),fg_color="steelblue3")
    button_select.grid(row=1, column=2, pady=10, sticky="N")

    # set label name between insert - "Choose one option"
    label_name2=customtkinter.CTkLabel(master=frame, text=language[3], text_color=("snow3","black"), text_font=("Verdana","11","bold"))
    label_name2.grid(row=2, column=2, sticky="N")

    # set line to entry URL of image 
    entry_URL=customtkinter.CTkEntry(master=frame, height=25, width=175, placeholder_text=language[4], placeholder_text_color=("steelblue3","black"), text_color="steelblue3", fg_color=("white","snow4"), border_color="gray40")
    entry_URL.grid(row=3, column=2, pady=10, sticky="N")

    # set label for setting row - "Setting"
    label_name3=customtkinter.CTkLabel(master=frame, text=language[5], text_color=("snow3","black"), text_font=("Verdana","12","bold"))
    label_name3.grid(row=4, column=0, pady=20, columnspan=2, sticky="E")

    # set checkbox to download
    checkbox_download=customtkinter.CTkCheckBox(master=frame, command=downloadstate, text=language[6], text_font=("Verdana","10","bold"), text_color=("snow3","black"), fg_color="steelblue3", border_color="gray40",hover_color="steelblue3")
    checkbox_download.grid(row=4, column=2,padx=30, pady=22, columnspan=2,sticky="W")

    # set menu to select size of output
    optionmenu=customtkinter.CTkOptionMenu(master=frame, command=menu, height=25, width=175, fg_color="steelblue3", button_color=("steelblue2"), button_hover_color=("snow3","snow2"), text_color=("white","black"), dropdown_color="steelblue3", dropdown_hover_color=("snow3","snow2") ,dropdown_text_color=("white","black"), values=[language[8],language[9],language[10]])
    optionmenu.grid(row=4, column=3, pady=22, columnspan=2, sticky="W")
    optionmenu.set(language[7])

    # set button generate text form of image
    button_generate=customtkinter.CTkButton(master=frame, command=generate, width=200, text=language[11], text_font=("Verdana","20","bold"), text_color=("white","black"), hover_color=("snow3","snow2"),fg_color="steelblue3")
    button_generate.grid(row=5, column=2, pady=10, sticky="N")

    # switch light or dark theme
    switch_theme=customtkinter.CTkSwitch(master=frame, command=changetheme, text=language[12], text_font=("Verdana","9","bold"), text_color=("snow3","black"), fg_color="snow3", button_color="steelblue3", button_hover_color="steelblue3")
    switch_theme.grid(row=6, column=0, padx=10, pady=15, sticky="S")
    switch_theme.select()

    # set label "About" to open ReadME.txt
    label_name4=customtkinter.CTkLabel(master=frame, cursor= "hand2", text=language[13], text_color=("snow3","black"), text_font=("Verdana","8","bold"))
    label_name4.grid(row=6, column=2, pady=8, sticky="S")
    label_name4.bind("<Button-1>", lambda e:subprocess.Popen("notepad myfile.txt"))

    # switch language CZK or ENG
    switch_language=customtkinter.CTkSwitch(master=frame, command=changelanguage, text=language[14], text_font=("Verdana","9","bold"), text_color=("snow3","black"), fg_color="gray40", button_color="steelblue3", button_hover_color="steelblue3")
    switch_language.grid(row=6, column=4, pady=15, sticky="W")

    # run window
    ui.mainloop()

mainwindow()