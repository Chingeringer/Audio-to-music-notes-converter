
'''
Date created: 6/18/2020
Author: Chong Wang
Title: Audio to music notes converter
'''


from pyaudio import PyAudio, paInt16
import numpy as np
import pygame
from sys import exit
import wave
import keyboard as kb

#System variables
rate = 44100
chunk = int(rate/10)
expSensitivity = 5 #if in milivolts per pascal
lowestFreq = 0
stream = PyAudio().open(format=paInt16, channels=1, rate=rate, input=True, frames_per_buffer=chunk)
noteClasses = []
record = False
data = None
frames = []
playBack = False


#Graphic variables
pygame.init()
fps = 60
clock = pygame.time.Clock()
width = 700
height = 700
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("The Oh Great And Powerful Music Practice Tool")
clef = pygame.image.load("sprites/clef.png").convert_alpha()
wholeNote = pygame.image.load("sprites/whole_note.png").convert_alpha()
sharp = pygame.image.load("sprites/sharp.png").convert_alpha()
line = pygame.Surface((30, 2))
line.fill((0, 0, 0))
font = pygame.font.SysFont("Arial", 20)
font2 = pygame.font.SysFont("Arial", 16)


def centerOctave(note):
    if note > 51:
        return centerOctave(note - 12)
    elif note < 40:
        return centerOctave(note + 12)
    else:
        return note


class noteData:
    def __init__(self, number, offTune): #maybe add area of note
        self.number = number
        self.offTune = offTune
    def sharp(self):
        centerNote = centerOctave(self.number)
        if centerNote in [41, 43, 46, 48, 50]:
            return True
        else:
            return False
    def name(self):
        noteNames = ["C", "C#/Db", "D", "D#/Eb", "E", "F", "F#/Gb", "G", "G#/Ab", "A", "A#/Bb", "B"]
        return noteNames[centerOctave(self.number) - 40]


def offTune(PSD, notes):
    output = [] #Create empty list
    for i in notes:
        i = int(i)#Remove decimal point
        lowLocation = round(4400*(2**((i-49.5)/12))) #Get the low end of the frequency range
        highLocation = round(4400*(2**((i-48.5)/12))) #Get the high end of the frequency range
        noteRange = PSD[lowLocation:highLocation] #Locate the range in the PSD
        noteFreq = np.where(noteRange == max(noteRange)) #Find the peak in the frequency range
        noteFreq = noteFreq[0] #Convert from list to integer
        Diff = round(4400*(2**((i-49.5)/12))) + noteFreq[0] #gets frequency
        Diff = round((12 * np.log2(Diff / 4400) + 49 - i)*100) #gets frequency difference in cents
        if Diff not in [50,-50, 49, -49]: #Remove neighboring intensity influence
            output.append([i, Diff]) # Append note and off tune amount in a 2-D list
    return output # Returns the output


def createNotedata(offTune):
    noteClasses = []
    if type(offTune) is list:
        for i in range(len(offTune)):
            n = noteData(offTune[i][0],offTune[i][1])
            noteClasses.append(n)
    return noteClasses


def sensitivity_change(up, down):
    global expSensitivity
    if down:
        expSensitivity = expSensitivity - 0.1
    if up:
        expSensitivity = expSensitivity + 0.1
    if expSensitivity > 10:
        expSensitivity = 10
    if expSensitivity < 1.0:
        expSensitivity = 1.0
    return round((10 ** (2*expSensitivity)), 1)


def render(noteClasses):
    n = 0
    for i in noteClasses: #Treble Clef
        n = n + 1
        if i.number >= 40:
            if i.sharp() == False:
                screen.blit(wholeNote, (345, int(round((i.number - 40) * -3.5)) + 353))
            elif i.sharp() == True:
                screen.blit(wholeNote, (345, int(round((i.number - 41) * -3.5)) + 353))
                screen.blit(sharp, (333, int(round(i.number - 41) * -3.5) + 346))
            if i.number > 60:
                for z in range(int(np.ceil((i.number - 60)) / 3.5) + 1): #Counts the amount of ledger lines
                    if i.number in [67, 74]:
                        z = z - 1
                    screen.blit(line, (337, 284 - 12 * z))
            if i.number in [40, 41]:
                screen.blit(line, (337, 357))
            #Bass clef
        if i.number < 40:
            if i.sharp() == False:
                screen.blit(wholeNote, (345, int(round(np.abs(i.number - 40) * 3.5) + 394)))
            elif i.sharp() == True:
                screen.blit(wholeNote, (345, int(round(np.abs(i.number - 41) * 3.5) + 394)))
                screen.blit(sharp, (333, int(round(i.number - 41) * -3.5) + 388))
            if i.number < 21:
                for z in range(int(np.floor(np.abs(i.number - 21)) / 3.5) + 1):
                    screen.blit(line, (337, 469 + 12 * z))
        xSpace = n*80
        printName = font2.render(i.name() + str(i.offTune), True, (0, 0, 0), None)
        screen.blit(printName, (50 + xSpace + printName.get_width() // 2, 150))


def calcNote(data):
    data = np.frombuffer(data, np.int16) #Read from buffer
    data = np.fft.rfft(data, n= rate*10) #Compute Real Fourier Transformation
    PSD = abs(data * np.conj(data)) #Multiply by imaginary conjugate
    PSD = PSD[0:45000] #Resize array to remove to reduce data
    freq = np.array(np.where(PSD > (sensitivity_change(kb.is_pressed("up"), kb.is_pressed("down")) + max(PSD) * 0.6)))#Get the frequencies that exceed this threshold
    notes = np.round(12 * np.log2(freq / 4400) + 49) #Convert frequenciest to notes
    notes = notes[notes > 0] #Remove negative notes
    notes = np.unique(notes) #Remove duplicate notes
    if notes.size != 0:
        offTuneData = offTune(PSD, notes)#Calculate how much a note is off tune by
        classesToRender = createNotedata(offTuneData)#Create the note class for rendering
        render(classesToRender)#Render the class
    screen.blit(clef, (0, 259))#Render clef
    text = font.render("Sensitivity: " + str(round(expSensitivity, 1)), True, (0, 0, 0), None)
    instructions = font.render("Use up and down arrows to adjust sensitivity.", True, (0, 0, 0), None)
    screen.blit(instructions, (50, 100))
    screen.blit(text, (50, 50))

def liveAudio():
    global record
    data = stream.read(chunk)
    calcNote(data)
    recording = font.render("Press space to record or press enter to playback last recording.", True, (0, 0, 0), None)
    if kb.is_pressed("space") and pygame.mouse.get_focused():
        record = True
    if record == True:
        recordAudio(data)
        recording = font.render("Recording... Press 'ESC' to stop", True, (0, 0, 0), None)
        if kb.is_pressed("esc") and pygame.mouse.get_focused():
            record = False
    screen.blit(recording, (50, 600))


def playAudio():
    pbStream = PyAudio().open(format=paInt16, channels=1, rate=rate, output=True, frames_per_buffer=chunk)
    wf = wave.open("playback.wav", "rb")
    data = wf.readframes(chunk) #read first frame
    while len(data) > 0:
        screen.fill((255, 255, 255))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                stream.close()
                exit()
        pbStream.write(data) #Plays the frame of audio
        calcNote(data) #processes the frame in the same way
        data = wf.readframes(chunk)
        playing = font.render("Press 'ESC' to stop playing", True, (0, 0, 0), None)
        screen.blit(playing, (50, 600))
        if kb.is_pressed("esc") and pygame.mouse.get_focused(): #stops the audio playing and goes back to live audio
            break
        pygame.display.update()
        clock.tick(fps)
    pbStream.close() #closes playback stream


def recordAudio(data):
    global frames
    frames.append(data) #adds the data to an list
    if kb.is_pressed("esc") and pygame.mouse.get_focused(): #writes the list to "playback.wav"
        wf = wave.open("playback.wav", "wb")
        wf.setnchannels(1)
        wf.setsampwidth(PyAudio().get_sample_size(paInt16))
        wf.setframerate(rate)
        wf.writeframes(b''.join(frames))
        frames = []
        wf.close()


if __name__ == '__main__':
    while True:
        screen.fill((255, 255, 255))
        for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    stream.close()
                    exit()
        try:
            if playBack == False:
                liveAudio()
                if kb.is_pressed("enter") and pygame.mouse.get_focused():
                    playBack = True
            if playBack == True:
                playAudio()
                playBack = False
        except:
            noMic = font.render("No microphone detected. Please plug in Microphone.", True, (0, 0, 0), None)
            screen.blit(noMic, (50, 100))
        pygame.display.update()
        clock.tick(fps)