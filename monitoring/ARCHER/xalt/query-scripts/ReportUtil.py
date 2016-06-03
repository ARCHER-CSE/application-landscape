#
# Python module with base functions for querying the XALT database
#
import prettytable as pt
import numpy as np
import csv

def readProjectCSV(infile):
    """Read project metadata from a CSV file and return lists

    Args:
        infile (string): The name of the CSV file

    Returns:
        Tuple of lists:
           (
             projAreaD (dict, string): Project research area,
             projTypeD (dict, string): Project class,
             projFundD (dict, string): Project funding body
           )
    """
    projAreaD = {}
    projTypeD = {}
    projFundD = {}
    with open(infile, 'r') as csvfile:
       projectR = csv.reader(csvfile)
       for row in projectR:
          code = row[0].strip()
          projAreaD[code] = row[1].strip()
          projTypeD[code] = row[2].strip()
          projFundD[code] = row[3].strip()
    return (projAreaD, projTypeD, projFundD)

def printMatrix(catXA, labelX, catYA, labelY, matrixD, valuesLabel):
    """Print a numerical matrix of results nicely
    """
    matrixT = pt.PrettyTable([''] + catXA + ['Total', '%'])
    tot = np.sum(matrixD.values())
    ySumA = {}
    for x in catXA:
        ySumA[x] = 0
    for y in catYA:
        xA = [y]
        xSum = 0
        for x in catXA:
            val = matrixD[(y, x)]
            xSum += val
            ySumA[x] += val
            xA.append(val)
        xA.append(xSum)
        px = 100.0 * (xSum/tot)
        xA.append(px)
        matrixT.add_row(xA)
    totRowA = ['Total']
    pRowA = ['%']
    for x in catXA:
        totRowA.append(ySumA[x])
        pRowA.append(100.0*ySumA[x]/tot)
    matrixT.add_row(totRowA + [tot, 100])
    matrixT.add_row(pRowA + [100.0, ''])

    matrixT.align = "r"
    matrixT.align[''] = "c"
    matrixT.float_format = '.3'
    print "\n{0} ({1} vs. {2})".format(valuesLabel, labelX, labelY)
    print matrixT, "\n"
