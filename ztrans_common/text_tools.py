def substitute_text(translation, text_source, sub_placeholder, sub_chars):
    #first get the proper order of text_source stuffs according to sub_chars
    l = list()
    last = False
    for char in text_source:
        if char in sub_chars:
            if last is False:
                last = True
                l.append(char)
            else:
                l[-1] = l[-1]+char
        else:
            last = False
    test_string = translation
    out_string = ""
    while sub_placeholder[0] in test_string and\
            sub_placeholder[1] in test_string.partition(sub_placeholder[0])[2]:
        p = test_string.partition(sub_placeholder[0])
        out_string += p[0]
        p2 = p[2].partition(sub_placeholder[1])
        try:
            val = int(p2[0])
            out_string += l[val]
        except:
            pass
        test_string = p2[2]
    out_string+=test_string
    return out_string

def levenshtein(s, t, max_dist=3):
    #as seen from https://www.python-course.eu/levenshtein_distance.php
    """ 
        iterative_levenshtein(s, t) -> ldist
        ldist is the Levenshtein distance between the strings 
        s and t.
        For all i and j, dist[i,j] will contain the Levenshtein 
        distance between the first i characters of s and the 
        first j characters of t
    """
    rows = len(s)+1
    cols = len(t)+1
    dist = [[0 for x in range(cols)] for x in range(rows)]
    # source prefixes can be transformed into empty strings 
    # by deletions:
    for i in range(1, rows):
        dist[i][0] = i
    # target prefixes can be created from an empty source string
    # by inserting the characters
    for i in range(1, cols):
        dist[0][i] = i
        
    for col in range(1, cols):
        for row in range(1, rows):
            if s[row-1] == t[col-1]:
                cost = 0
            else:
                cost = 1
            dist[row][col] = min(dist[row-1][col] + 1,      # deletion
                                 dist[row][col-1] + 1,      # insertion
                                 dist[row-1][col-1] + cost) # substitution
    #print dist[row][col]
    if dist[row][col] < max_dist:
        return True
    return False
    #return dist[row][col]

def levenshtein_shortcircuit(s, t, max_dist=3):
    #as seen from https://www.python-course.eu/levenshtein_distance.php
    """ 
        iterative_levenshtein(s, t) -> ldist
        ldist is the Levenshtein distance between the strings 
        s and t.
        For all i and j, dist[i,j] will contain the Levenshtein 
        distance between the first i characters of s and the 
        first j characters of t
    """
    rows = len(s)+1
    cols = len(t)+1
    if abs(rows-cols)> max_dist:
        return False

    dist = [[0 for x in range(cols)] for x in range(rows)]
    # source prefixes can be transformed into empty strings 
    # by deletions:
    for i in range(1, rows):
        dist[i][0] = i
    # target prefixes can be created from an empty source string
    # by inserting the characters
    for i in range(1, cols):
        dist[0][i] = i
        
    for col in range(1, cols):
        max_num = 1000000
        for row in range(1, rows):
            if s[row-1] == t[col-1]:
                cost = 0
            else:
                cost = 1
            dist[row][col] = min(dist[row-1][col] + 1,      # deletion
                                 dist[row][col-1] + 1,      # insertion
                                 dist[row-1][col-1] + cost) # substitution
            if dist[row][col] < max_num:
                max_num = dist[row][col]
        if max_num >= max_dist:
            return False
    #print dist[row][col]
    if dist[row][col] < max_dist:
        return True
    return False
    #return dist[row][col]

def levenshtein_shortcircuit_dist(s, t, max_dist=3):
    #as seen from https://www.python-course.eu/levenshtein_distance.php
    """ 
        iterative_levenshtein(s, t) -> ldist
        ldist is the Levenshtein distance between the strings 
        s and t.
        For all i and j, dist[i,j] will contain the Levenshtein 
        distance between the first i characters of s and the 
        first j characters of t
    """
    rows = len(s)+1
    cols = len(t)+1
    if abs(rows-cols)> max_dist:
        return False, 10000

    dist = [[0 for x in range(cols)] for x in range(rows)]
    # source prefixes can be transformed into empty strings 
    # by deletions:
    for i in range(1, rows):
        dist[i][0] = i
    # target prefixes can be created from an empty source string
    # by inserting the characters
    for i in range(1, cols):
        dist[0][i] = i
        
    for col in range(1, cols):
        max_num = 1000000
        for row in range(1, rows):
            if s[row-1] == t[col-1]:
                cost = 0
            else:
                cost = 1
            dist[row][col] = min(dist[row-1][col] + 1,      # deletion
                                 dist[row][col-1] + 1,      # insertion
                                 dist[row-1][col-1] + cost) # substitution
            if dist[row][col] < max_num:
                max_num = dist[row][col]
        if max_num >= max_dist:
            return False, 100000
    #print dist[row][col]
    if dist[row][col] < max_dist:
        return True, dist[row][col]
    return False, 100000
    #return dist[row][col]
