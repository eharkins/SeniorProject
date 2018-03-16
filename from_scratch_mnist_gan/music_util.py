import os, cv2, math
from music21 import midi, stream, pitch, note, tempo, chord, instrument
import numpy as np

# music stuff
# lowest_pitch = 30
# highest_pitch = 127
# note_range = highest_pitch-lowest_pitch
lowest_pitch = 30
highest_pitch = 127
note_range = highest_pitch-lowest_pitch
beats_per_measure = 16
measures_per_minisong = 1
beats_per_minisong = beats_per_measure * measures_per_minisong
instrument_list = []
MAX_VOL = 127


# LENGTH PER BEAT IS THE STANDARDIZED LENGTH OF NOTES/RESTS
# IT IS USED IN THE CALCULATION OF HOW MANY SONGS WE CAN CREATE
# IT EFFECTIVELY DEFINES THE MEASURE LENGTH
lengthPerBeat = 0.25
song_tempo = 100

# put the pitches into the corresponding index in the array
def addNote(notes, final_tracks, measure_in_song, minisong, track_n):
    for note in notes:
        position = int(note.offset/lengthPerBeat) + measure_in_song * beats_per_measure
        if note.isChord:
          for p in note.pitches:
            final_tracks[minisong, position, p.midi-lowest_pitch, track_n] = 1 #note.volume.velocity/MAX_VOL
        elif not note.isRest:
            final_tracks[minisong, position, note.pitch.midi-lowest_pitch, track_n] = 1 #note.volume.velocity/MAX_VOL


def get_standardized_note_tracks(num_songs, beats_per_minisong, tracks):
    #first dimension is minisong number * notes per minisong
  #final_tracks = np.zeros((longest_track, note_range, len(tracks)))
  final_tracks = np.zeros((num_songs, beats_per_minisong, note_range, len(tracks)))
  print ("tracks size is: ", len(tracks))
  print ("final tracks shape is: ", final_tracks.shape)
  global instrument_list
  for track_n in range(len(tracks)):
    track = tracks[track_n]
    # add our instrument to the array to keep track of instruments on each channel
    inst = track.getInstrument()
    inst_name = inst.instrumentName
    print(inst_name)
    print ("instrument", track_n, " is: ", inst_name)
    # print("notes: ")
    # notes.show('text')
    global instrument_list
    instrument_list.append(inst)
    if(inst_name == None):
        continue
        print("NO INSTRUMENT")
    measures = track.flat.notes.stream().measures(0, None)
    measures = measures.getElementsByClass("Measure")
    print ("number of measures: ", len(measures))
    for measure in range(len(measures)):
        m = measures[measure]
        minisong = int(measure/measures_per_minisong)
        measure_in_song = measure%measures_per_minisong
        if m.voices:
            for v in m.voices:
                addNote(v.notes, final_tracks, measure_in_song, minisong, track_n)
        else:
            addNote(m.notes, final_tracks, measure_in_song, minisong, track_n)
  return final_tracks

def loadMidi(data_source):
    mf = midi.MidiFile()
    mf.open(filename = data_source)
    mf.read()
    mf.close()

    #read to stream
    s = midi.translate.midiFileToStream(mf)
    #s = instrument.partitionByInstrument(a)
    metronome = s.metronomeMarkBoundaries()[0]
    temp = metronome[2].getQuarterBPM()
    global song_tempo
    # set the tempo of the song to match it when we remidify
    song_tempo = temp

    #number of parts/instruments
    tracks = s.parts
    #tracks = tracks[:3]
    print("CHANNELS : ", len(tracks))
    channels = len(tracks)
    data_shape = (beats_per_minisong, note_range, channels)

    # number of possible songs in the longest track
    longest_length = 0
    for track in tracks:
        print("track length: ", track.duration.quarterLength)
        # print("length :", length)
        longest_length = max(longest_length, track.duration.quarterLength)
    print("longest length is: ", longest_length)
    mybeats = longest_length/lengthPerBeat
    num_songs = math.ceil(mybeats/beats_per_minisong)

    minisongs = get_standardized_note_tracks(num_songs, beats_per_minisong, tracks)
    # cut short to 30 songs
    #minisongs = minisongs[:15]

    # reshape to break them into "measures" as defined by beats_per_minisong
    #minisongs = np.reshape(standardized_tracks, ((num_songs,) + data_shape)  )

    return minisongs, data_shape

def reMIDIfy(minisong, output):
    # each note
    s1 = stream.Stream()
    # assign the tempo based on what was read in
    t = tempo.MetronomeMark('fast', song_tempo, note.Note(type='quarter'))
    # t = tempo.MetronomeMark('fast', 240, note.Note(type='quarter'))
    s1.append(t)
    #minisong = minisong.reshape((beats_per_minisong, note_range, channels))
    channels = minisong.shape[2]
    #data_shape = (beats_per_minisong, note_range, channels)
    for curr_channel in range(channels):
        new_part = stream.Part([instrument_list[curr_channel]])
        for beat in range(beats_per_minisong):
            notes = []
            for curr_pitch in range(note_range):
                #if this pitch is produced with at least 10% likelihood then count it
                if minisong[beat][curr_pitch][curr_channel]>.1:
                    p = pitch.Pitch()
                    p.midi = curr_pitch+lowest_pitch
                    n = note.Note(pitch = p)
                    n.pitch = p
                    n.volume.velocity = minisong[beat][curr_pitch][curr_channel]*MAX_VOL
                    n.quarterLength = lengthPerBeat
                    notes.append(n)
            if notes:
                my_chord = chord.Chord(notes)

            else:
                my_chord = note.Rest()
                my_chord.quarterLength = lengthPerBeat

            new_part.append(my_chord)
        s1.insert(curr_channel, new_part)

    mf = midi.translate.streamToMidiFile(s1)
    mf.open(output + ".mid", 'wb')
    mf.write()
    mf.close()

def playSong(music_file):
    #clock = pygame.time.Clock()
    try:
        pygame.mixer.music.load(music_file)
        print ("playing song:", music_file)
    except pygame.error:
        print ("File %s not found! (%s)" % (music_file, pygame.get_error()))
        return
    except KeyboardInterrupt:
        # if user hits Ctrl/C then exit
        # (works only in console mode)
        pygame.mixer.music.fadeout(1000)
        pygame.mixer.music.stop()
        raise SystemExit
    pygame.mixer.music.play()
    # while pygame.mixer.music.get_busy():
    #     # check if playback has finished
    #     clock.tick(30)



def saveMidi(notesData, epoch, output_dir):
    f = output_dir+"/song_"+str(epoch)
    reMIDIfy(notesData[0], f)
    #print (" saving song as ", f)
    # if not pygame.mixer.music.get_busy():
    #     playSong(f)

def writeCutSongs(notesData, directory = "output/midi_input"):
    if not os.path.exists(directory):
        os.makedirs(directory)
    #print ("number of song fragments: ", len(notesData))
    #print ("shape of notes is: ", notesData.shape)
    #notesData = notesData[:,:,:,:3] # this should be removed ultimately but currently drum tracks get turned into piano and sound terrible
    for x in range(len(notesData)):
        reMIDIfy(notesData[x], directory+"/input_song_"+str(x))
        #cv2.imwrite(directory+"/input_score_%d.png" % x, notesData[x]*255)
