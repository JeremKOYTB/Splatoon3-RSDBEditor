import os
import webbrowser
import darkdetect
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QLineEdit, QCheckBox, QComboBox, QLabel, QPushButton, 
                             QSplitter, QFrame, QTableWidget, QAbstractItemView, 
                             QStackedWidget, QTreeWidget, QHeaderView, QFormLayout, 
                             QSpinBox, QMenu, QMenuBar, QSizePolicy, QTableWidgetItem,
                             QDialog, QApplication, QMessageBox, QProgressBar)
from PyQt6.QtCore import Qt, QSize, QByteArray, QRegularExpression
from PyQt6.QtGui import QAction, QCursor, QImage, QPainter, QIcon, QPixmap, QFontMetrics, QFont, QRegularExpressionValidator

from translations import t
from utils import get_hide_filenames, get_hide_coop, get_hide_mission, get_hide_notfound, log, CACHE_DIR

S3RSDB_MAIN_LOGO = b"""<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 20010904//EN"
 "http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd">
<svg version="1.0" xmlns="http://www.w3.org/2000/svg"
 width="2000.000000pt" height="1889.000000pt" viewBox="0 0 2000.000000 1889.000000"
 preserveAspectRatio="xMidYMid meet">
<g transform="translate(0.000000,1889.000000) scale(0.100000,-0.100000)" fill="#000000" stroke="none">
<path d="M8945 18829 c-902 -60 -2016 -271 -3185 -604 -899 -256 -1735 -648
-2610 -1223 -524 -344 -1129 -810 -1434 -1103 -799 -767 -1344 -1921 -1616
-3419 -64 -354 -74 -470 -75 -850 0 -358 7 -460 55 -800 101 -707 333 -1492
690 -2329 148 -349 261 -561 445 -841 265 -404 572 -768 1006 -1195 455 -446
975 -880 1557 -1298 106 -76 149 -114 211 -189 103 -123 349 -361 486 -471
208 -166 455 -333 688 -463 53 -30 97 -59 97 -64 0 -25 -47 -154 -76 -210 -84
-161 -224 -265 -429 -321 -118 -32 -376 -32 -524 0 -627 137 -1167 611 -1375
1208 -33 97 -77 279 -91 375 -5 36 -22 69 -71 140 -190 270 -374 375 -690 394
-103 6 -115 5 -158 -16 -40 -19 -54 -35 -101 -114 -29 -51 -94 -173 -143 -273
-485 -984 -552 -1923 -197 -2753 148 -346 408 -707 700 -972 533 -484 1218
-790 1922 -859 152 -15 506 -6 633 16 300 51 557 150 772 297 115 78 295 255
373 367 181 260 295 627 295 953 0 66 3 88 13 88 26 0 138 -76 196 -133 180
-175 241 -401 158 -580 -58 -127 -164 -218 -357 -309 -226 -107 -248 -119
-298 -167 -117 -112 -140 -254 -65 -408 35 -73 170 -211 270 -277 308 -202
751 -345 1263 -408 137 -17 613 -17 740 0 654 88 1129 304 1544 702 146 139
320 363 416 534 39 68 28 75 116 -68 111 -180 272 -373 432 -519 379 -347 868
-564 1447 -643 181 -25 635 -25 820 -1 394 53 704 139 994 278 294 141 458
283 520 452 42 114 20 237 -58 327 -55 64 -97 91 -258 164 -238 107 -361 207
-426 343 -29 62 -32 77 -32 163 0 149 54 275 172 401 49 52 184 149 209 149
10 0 14 -14 14 -53 0 -86 20 -264 41 -372 131 -659 609 -1121 1303 -1260 201
-40 310 -48 556 -42 294 7 479 37 775 122 901 262 1654 891 2010 1682 342 759
315 1655 -77 2563 -60 137 -227 468 -271 536 -58 89 -125 107 -317 84 -194
-24 -342 -92 -465 -215 -44 -44 -109 -122 -144 -173 -59 -88 -64 -98 -81 -196
-39 -216 -85 -357 -175 -536 -250 -497 -740 -874 -1288 -992 -146 -31 -386
-31 -509 0 -246 61 -425 226 -492 455 l-14 48 60 37 c75 46 276 190 343 246
28 23 120 94 205 158 202 151 378 305 520 458 187 200 196 209 410 362 554
399 1064 825 1504 1258 438 432 739 788 1001 1185 184 279 301 500 445 840
390 919 621 1731 715 2505 11 95 15 240 15 620 0 536 -2 558 -66 905 -189
1024 -523 1917 -978 2610 -336 511 -672 849 -1376 1381 -1096 830 -2179 1390
-3297 1708 -960 273 -1947 478 -2698 561 -441 49 -420 48 -1490 50 -561 2
-1078 -1 -1150 -6z m2050 -329 c88 -5 192 -12 230 -15 l70 -6 -64 -67 c-121
-127 -210 -286 -247 -438 -25 -100 -23 -277 4 -375 153 -565 868 -959 1741
-959 199 0 336 13 524 51 719 143 1197 545 1243 1047 4 40 8 72 9 72 10 0 340
-121 347 -128 4 -4 4 -46 0 -92 -35 -351 140 -668 453 -825 133 -66 239 -88
395 -82 70 2 152 12 185 21 131 36 282 125 375 220 24 25 48 46 52 46 26 0
606 -381 842 -553 147 -107 396 -297 396 -303 0 -2 -23 -32 -51 -66 -224 -277
-224 -660 2 -935 152 -187 417 -289 654 -253 146 22 292 89 387 178 l47 44 31
-44 c60 -82 180 -276 262 -424 336 -607 600 -1413 747 -2279 110 -648 66
-1357 -135 -2160 -170 -678 -515 -1595 -772 -2050 -401 -712 -1085 -1456
-2044 -2223 -131 -106 -575 -442 -583 -442 -2 0 4 19 14 43 64 148 147 452
180 652 46 284 52 656 16 924 -184 1348 -1189 2421 -2515 2685 -202 40 -374
56 -615 56 -502 0 -926 -95 -1363 -305 -343 -166 -588 -340 -863 -614 -224
-224 -388 -439 -538 -707 -128 -230 -251 -548 -309 -804 -18 -78 -31 -117 -35
-105 -3 11 -17 68 -31 126 -97 410 -281 800 -547 1154 -528 705 -1329 1157
-2208 1245 -133 13 -489 13 -622 0 -881 -87 -1680 -538 -2213 -1247 -347 -462
-550 -977 -617 -1568 -16 -142 -17 -508 -1 -650 36 -317 120 -643 236 -913
l35 -82 -62 42 c-101 69 -581 432 -722 547 -376 306 -578 485 -874 776 -634
624 -1046 1188 -1314 1800 -424 970 -671 1838 -753 2655 -21 204 -24 682 -5
850 37 339 147 882 256 1260 149 520 355 1020 583 1418 104 181 222 357 231
346 258 -295 499 -442 841 -515 148 -32 390 -31 540 0 580 122 1001 547 1117
1127 26 133 24 395 -5 531 -52 239 -145 434 -300 626 -30 37 -53 69 -51 71 35
30 592 346 611 346 4 0 8 -6 8 -14 0 -8 22 -58 50 -113 174 -345 494 -569 880
-614 428 -49 854 166 1083 546 148 247 191 582 111 861 -14 49 -28 98 -31 109
-4 18 9 24 149 58 254 64 641 153 848 196 207 42 642 121 669 121 9 0 -8 -14
-37 -31 -68 -38 -192 -156 -247 -234 -191 -270 -219 -615 -72 -910 117 -237
352 -417 614 -471 96 -20 317 -14 408 11 94 26 236 99 319 165 143 113 259
293 307 475 30 113 30 317 0 430 -56 213 -191 403 -366 519 -65 44 -180 98
-245 117 l-45 13 130 13 c72 7 195 16 275 21 201 13 1800 14 1995 2z m-3600
-10175 c588 -90 1111 -454 1400 -975 492 -887 217 -2005 -630 -2563 -241 -159
-519 -262 -813 -303 -147 -20 -447 -15 -581 10 -422 79 -785 274 -1077 578
-625 653 -711 1661 -205 2414 310 462 823 782 1351 843 52 6 109 13 125 15 58
8 331 -4 430 -19z m6029 0 c574 -88 1084 -434 1380 -937 328 -558 353 -1248
67 -1833 -287 -585 -837 -981 -1489 -1071 -147 -20 -447 -15 -581 10 -328 61
-628 196 -876 394 -911 727 -985 2075 -160 2897 296 295 709 498 1105 544 52
6 109 13 125 15 58 8 331 -4 429 -19z m-3273 -2565 c63 -215 181 -483 300
-686 408 -693 1068 -1210 1831 -1433 316 -92 547 -124 893 -124 475 0 809 69
1292 270 7 3 16 -3 19 -13 109 -314 347 -542 659 -632 145 -42 186 -47 390
-47 235 0 344 18 565 91 572 190 1064 627 1316 1171 62 134 127 333 157 481
25 121 26 125 84 200 73 94 154 152 246 175 126 32 111 44 220 -175 288 -583
410 -1078 394 -1607 -7 -244 -35 -422 -97 -626 -212 -693 -723 -1263 -1445
-1611 -852 -411 -1784 -388 -2291 57 -197 174 -326 402 -384 684 -28 132 -42
329 -34 466 8 136 -1 174 -51 218 -47 41 -104 55 -190 46 -104 -9 -180 -31
-282 -80 -254 -123 -459 -377 -524 -651 -30 -126 -24 -295 15 -409 38 -112 96
-205 188 -301 119 -124 257 -211 480 -304 102 -42 106 -47 66 -99 -118 -150
-495 -325 -885 -410 -608 -131 -1195 -95 -1693 104 -270 108 -472 239 -679
440 -218 212 -380 448 -506 736 -25 57 -58 116 -72 131 -52 54 -138 61 -208
18 -27 -17 -44 -41 -72 -103 -179 -394 -371 -660 -631 -878 -375 -312 -816
-478 -1382 -520 -561 -41 -1250 112 -1626 359 -83 55 -174 139 -174 161 0 16
51 45 158 90 501 211 731 599 607 1025 -81 280 -311 537 -570 637 -181 70
-347 75 -417 12 -45 -41 -49 -62 -52 -311 -3 -259 -14 -344 -66 -514 -183
-591 -742 -924 -1505 -895 -1089 42 -2134 754 -2515 1713 -245 616 -219 1322
77 2079 66 170 240 524 261 532 23 9 128 -14 187 -41 65 -30 133 -91 191 -172
38 -53 46 -74 64 -167 157 -813 803 -1494 1614 -1702 176 -45 306 -59 490 -52
207 8 340 39 501 118 226 111 412 328 484 564 7 22 14 46 17 53 3 9 17 6 54
-13 79 -40 254 -110 375 -149 787 -254 1625 -193 2370 174 486 240 912 610
1214 1055 238 350 373 671 486 1150 6 25 11 14 31 -75 13 -58 38 -152 55 -210z"/>
<path d="M10878 16420 c-206 -33 -370 -114 -506 -251 -184 -185 -273 -419
-259 -677 22 -385 273 -694 654 -804 114 -33 343 -33 458 0 307 89 546 331
626 637 31 115 31 308 1 427 -66 266 -261 498 -504 600 -146 62 -337 89 -470
68z"/>
<path d="M6387 15870 c-956 -151 -1545 -1102 -1246 -2015 169 -515 617 -915
1147 -1026 765 -160 1523 272 1781 1014 61 174 75 270 75 497 0 226 -13 310
-74 493 -150 446 -517 816 -960 967 -163 55 -265 72 -470 75 -107 2 -221 0
-253 -5z"/>
<path d="M14275 15489 c-466 -36 -885 -329 -1089 -760 -167 -352 -167 -776 0
-1128 181 -383 525 -653 944 -742 148 -31 372 -31 520 0 276 58 511 189 703
391 596 626 445 1640 -308 2073 -147 85 -347 149 -501 162 -138 11 -171 12
-269 4z"/>
<path d="M8992 13965 c-104 -23 -207 -80 -288 -160 -132 -131 -191 -284 -181
-470 9 -166 61 -281 182 -401 117 -116 255 -174 417 -174 115 0 176 14 278 62
119 57 221 159 278 278 48 101 62 163 62 273 0 165 -63 312 -184 432 -148 146
-356 205 -564 160z"/>
<path d="M17230 13469 c-282 -32 -556 -190 -727 -417 -282 -374 -296 -862 -37
-1259 49 -76 213 -238 289 -288 380 -248 846 -246 1217 6 80 55 188 158 249
238 63 83 151 262 178 361 102 378 -6 781 -283 1055 -175 173 -393 277 -639
304 -107 12 -139 12 -247 0z"/>
<path d="M3266 13384 c-274 -66 -495 -378 -556 -784 -6 -41 -11 -138 -11 -215
0 -157 11 -248 47 -381 117 -440 427 -695 752 -619 363 86 613 570 572 1110
-45 590 -403 986 -804 889z"/>
<path d="M6916 7255 c-156 -30 -272 -92 -391 -210 -116 -115 -177 -228 -209
-387 -65 -317 91 -642 384 -801 187 -102 429 -115 630 -34 150 61 291 183 369
322 70 122 94 215 95 365 1 152 -10 202 -76 340 -44 92 -61 115 -142 195 -69
69 -110 101 -173 133 -149 77 -332 106 -487 77z"/>
<path d="M13054 7255 c-152 -27 -271 -86 -379 -187 -173 -162 -255 -362 -242
-593 22 -414 369 -723 787 -702 588 29 911 702 566 1180 -116 162 -284 267
-481 302 -103 18 -155 18 -251 0z"/>
</g>
</svg>"""
SVG_X_DARK = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24"><path fill="#E8E8E8" d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>"""
SVG_X_LIGHT = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24"><path fill="#1D1D1F" d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>"""

SVG_GITHUB_DARK = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24"><path fill="#E8E8E8" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.008.069-.008 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/></svg>"""
SVG_GITHUB_LIGHT = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24"><path fill="#1D1D1F" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.008.069-.008 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/></svg>"""

SVG_DISCORD_DARK = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24"><path fill="#E8E8E8" d="M20.317 4.37a19.791 19.791 0 00-4.885-1.515.074.074 0 00-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 00-5.487 0 12.64 12.64 0 00-.617-1.25.077.077 0 00-.079-.037A19.736 19.736 0 003.677 4.37a.07.07 0 00-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 00.031.057 19.9 19.9 0 005.993 3.03.078.078 0 00.084-.028c.462-.63.874-1.295 1.226-1.994.021-.041.001-.09-.041-.106a13.094 13.094 0 01-1.873-.894.077.077 0 01-.008-.128c.126-.093.252-.19.372-.287a.075.075 0 01.077-.011c3.92 1.793 8.18 1.793 12.061 0a.073.073 0 01.078.009c.12.099.246.195.373.289a.075.075 0 01-.006.127 12.298 12.298 0 01-1.873.894.077.077 0 01-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 00.084.028 19.839 19.839 0 006.002-3.03a.077.077 0 00.032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 00-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.156-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.156 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.156-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.156 2.418z"/></svg>"""
SVG_DISCORD_LIGHT = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24"><path fill="#1D1D1F" d="M20.317 4.37a19.791 19.791 0 00-4.885-1.515.074.074 0 00-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 00-5.487 0 12.64 12.64 0 00-.617-1.25.077.077 0 00-.079-.037A19.736 19.736 0 003.677 4.37a.07.07 0 00-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 00.031.057 19.9 19.9 0 005.993 3.03.078.078 0 00.084-.028c.462-.63.874-1.295 1.226-1.994.021-.041.001-.09-.041-.106a13.094 13.094 0 01-1.873-.894.077.077 0 01-.008-.128c.126-.093.252-.19.372-.287a.075.075 0 01.077-.011c3.92 1.793 8.18 1.793 12.061 0a.073.073 0 01.078.009c.12.099.246.195.373.289a.075.075 0 01-.006.127 12.298 12.298 0 01-1.873.894.077.077 0 01-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 00.084.028 19.839 19.839 0 006.002-3.03a.077.077 0 00.032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 00-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.156-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.156 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.156-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.156 2.418z"/></svg>"""

def get_app_icon():
    svg_data = S3RSDB_MAIN_LOGO
    if darkdetect.isDark():
        svg_data = svg_data.replace(b'fill="#000000"', b'fill="#FFFFFF"')
    pix = QPixmap()
    pix.loadFromData(QByteArray(svg_data))
    return QIcon(pix)

def get_stylesheet(is_dark):
    if is_dark:
        return """
        QWidget { font-family: "Segoe UI Variable", "Segoe UI", "Roboto", sans-serif; font-size: 10pt; }
        QFrame#Card { background-color: rgba(0, 0, 0, 40); border-radius: 8px; border: 1px solid rgba(0, 0, 0, 100); }
        QPushButton { border-radius: 6px; padding: 6px 14px; border: 1px solid rgba(0, 0, 0, 100); background-color: rgba(255, 255, 255, 20); outline: none; }
        QPushButton:focus { outline: none; }
        QPushButton:hover { background-color: rgba(255, 255, 255, 40); }
        QPushButton:pressed { background-color: rgba(0, 0, 0, 40); }
        QComboBox, QLineEdit, QSpinBox { border-radius: 6px; padding: 5px; border: 1px solid rgba(0, 0, 0, 100); background-color: rgba(0, 0, 0, 40); color: white; }
        QComboBox::drop-down { border: none; }
        QTableWidget, QTreeWidget { border: none; background-color: transparent; outline: none; }
        QTableWidget::item { padding: 4px; background-color: transparent; border: none; }
        QTableWidget::item:selected, QTableWidget::item:selected:!active { background-color: #0078D7; color: white; border: none; outline: none; }
        QTableWidget::item:hover { background-color: rgba(255, 255, 255, 20); }
        QTreeWidget:focus { outline: none; }
        QTreeWidget::item { padding: 4px; }
        QTreeWidget QLineEdit { background-color: #2b2b2b; color: white; border: 1px solid #0078D7; border-radius: 0px; padding: 0px 2px; margin: -1px 0px; }
        QMenu { background-color: #2c3e50; color: white; border: 1px solid #34495e; }
        QMenu::item:selected { background-color: #3498db; }
        #btnSocial { background-color: transparent; border: none; padding: 2px; border-radius: 4px; }
        #btnSocial:hover { background-color: rgba(255, 255, 255, 40); }
        QMenuBar { border-bottom: 1px solid rgba(0, 0, 0, 100); background-color: transparent; }
        QMenuBar::item { padding: 6px 12px; background-color: transparent; border: none; outline: none; }
        QMenuBar::item:selected { background-color: rgba(255, 255, 255, 20); border-radius: 4px; }
        QHeaderView::section { background-color: rgba(0, 0, 0, 40); color: white; padding: 4px; border: none; border-bottom: 1px solid rgba(0, 0, 0, 100); border-right: 1px solid rgba(0, 0, 0, 100); }
        #CountLabel { color: #cccccc; font-weight: bold; margin-bottom: 5px; }
        """
    else:
        return """
        QWidget { font-family: "Segoe UI Variable", "Segoe UI", "Roboto", sans-serif; font-size: 10pt; color: #1D1D1F; }
        QFrame#Card { background-color: rgba(255, 255, 255, 180); border-radius: 8px; border: 1px solid rgba(0, 0, 0, 30); }
        QPushButton { border-radius: 6px; padding: 6px 14px; border: 1px solid rgba(0, 0, 0, 40); background-color: rgba(255, 255, 255, 255); outline: none; color: #1D1D1F; }
        QPushButton:focus { outline: none; }
        QPushButton:hover { background-color: rgba(0, 0, 0, 10); }
        QPushButton:pressed { background-color: rgba(0, 0, 0, 20); }
        QComboBox, QLineEdit, QSpinBox { border-radius: 6px; padding: 5px; border: 1px solid rgba(0, 0, 0, 40); background-color: rgba(255, 255, 255, 255); color: #1D1D1F; }
        QComboBox::drop-down { border: none; }
        QTableWidget, QTreeWidget { border: none; background-color: transparent; outline: none; color: #1D1D1F; }
        QTableWidget::item { padding: 4px; background-color: transparent; border: none; }
        QTableWidget::item:selected, QTableWidget::item:selected:!active { background-color: #0078D7; color: white; border: none; outline: none; }
        QTableWidget::item:hover { background-color: rgba(0, 0, 0, 10); }
        QTreeWidget:focus { outline: none; }
        QTreeWidget::item { padding: 4px; }
        QTreeWidget QLineEdit { background-color: #ffffff; color: #1D1D1F; border: 1px solid #0078D7; border-radius: 0px; padding: 0px 2px; margin: -1px 0px; }
        QMenu { background-color: #ffffff; color: #1D1D1F; border: 1px solid #cccccc; }
        QMenu::item:selected { background-color: #0078D7; color: white; }
        #btnSocial { background-color: transparent; border: none; padding: 2px; border-radius: 4px; }
        #btnSocial:hover { background-color: rgba(0, 0, 0, 10); }
        QMenuBar { border-bottom: 1px solid rgba(0, 0, 0, 40); background-color: transparent; }
        QMenuBar::item { padding: 6px 12px; background-color: transparent; border: none; outline: none; color: #1D1D1F; }
        QMenuBar::item:selected { background-color: rgba(0, 0, 0, 10); border-radius: 4px; }
        QHeaderView::section { background-color: rgba(240, 240, 245, 255); color: #1D1D1F; padding: 4px; border: none; border-bottom: 1px solid rgba(0, 0, 0, 40); border-right: 1px solid rgba(0, 0, 0, 40); }
        #CountLabel { color: #555555; font-weight: bold; margin-bottom: 5px; }
        """

class AboutDialog(QDialog):
    def __init__(self, parent, is_dark, version):
        super().__init__(parent)
        self.setWindowTitle(t("menu_about"))
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.MSWindowsFixedSizeDialogHint)
        self.is_dark = is_dark
        self.version = version
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        top_layout = QHBoxLayout()
        
        logo_lbl = QLabel(self)
        px_logo = QPixmap()
        px_logo.loadFromData(QByteArray(S3RSDB_MAIN_LOGO))
        if self.is_dark:
            px_logo = QPixmap()
            svg_data = S3RSDB_MAIN_LOGO.replace(b'fill="#000000"', b'fill="#FFFFFF"')
            px_logo.loadFromData(QByteArray(svg_data))
            
        logo_lbl.setPixmap(px_logo.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        top_layout.addWidget(logo_lbl, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        top_layout.addStretch(1)
        
        social_layout = QHBoxLayout()
        social_layout.setSpacing(8)

        btn_x = QPushButton(self)
        btn_x.setObjectName("btnSocial")
        btn_x.setFixedSize(36, 36)
        px_x = QPixmap()
        px_x.loadFromData(QByteArray(SVG_X_DARK if self.is_dark else SVG_X_LIGHT))
        btn_x.setIcon(QIcon(px_x))
        btn_x.setIconSize(QSize(20, 20))
        btn_x.clicked.connect(lambda: webbrowser.open("https://x.com/JeremKOYTB"))

        btn_git = QPushButton(self)
        btn_git.setObjectName("btnSocial")
        btn_git.setFixedSize(36, 36)
        px_git = QPixmap()
        px_git.loadFromData(QByteArray(SVG_GITHUB_DARK if self.is_dark else SVG_GITHUB_LIGHT))
        btn_git.setIcon(QIcon(px_git))
        btn_git.setIconSize(QSize(20, 20))
        btn_git.clicked.connect(lambda: webbrowser.open("https://github.com/JeremKOYTB/Splatoon3-RSDBEditor/"))

        btn_disc = QPushButton(self)
        btn_disc.setObjectName("btnSocial")
        btn_disc.setFixedSize(36, 36)
        px_disc = QPixmap()
        px_disc.loadFromData(QByteArray(SVG_DISCORD_DARK if self.is_dark else SVG_DISCORD_LIGHT))
        btn_disc.setIcon(QIcon(px_disc))
        btn_disc.setIconSize(QSize(20, 20))
        btn_disc.clicked.connect(self.copy_discord)

        social_layout.addWidget(btn_x)
        social_layout.addWidget(btn_git)
        social_layout.addWidget(btn_disc)
        
        top_layout.addLayout(social_layout)
        layout.addLayout(top_layout)

        info_lbl = QLabel(self)
        info_lbl.setWordWrap(True)
        info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_lbl.setText(t("about_desc", self.version))
        layout.addWidget(info_lbl)

        close_btn = QPushButton(t("diff_btn_close"), self)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.setFixedSize(380, 260)

    def copy_discord(self):
        QApplication.clipboard().setText("jeremko")
        QMessageBox.information(self, t("msg_copied"), t("msg_discord_copied"))

class CacheDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("cache_title"))
        self.setFixedSize(450, 120)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        
        layout = QVBoxLayout(self)
        self.lbl = QLabel(t("cache_desc"))
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl)
        
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

    def closeEvent(self, event):
        event.ignore()

class UILayoutMixin:
    def get_balanced_text(self, button, text, max_width):
        font = button.font()
        font.setBold(True)
        metrics = QFontMetrics(font)
        
        available_width = max_width - 28 

        if metrics.horizontalAdvance(text) <= available_width:
            return text

        words = text.split(' ')
        if len(words) <= 1:
            return text 

        best_split = 1
        min_diff = float('inf')

        for i in range(1, len(words)):
            line1 = ' '.join(words[:i])
            line2 = ' '.join(words[i:])
            
            w1 = metrics.horizontalAdvance(line1)
            w2 = metrics.horizontalAdvance(line2)
            
            diff = abs(w1 - w2)
            if diff < min_diff:
                min_diff = diff
                best_split = i

        return ' '.join(words[:best_split]) + '\n' + ' '.join(words[best_split:])

    def ask_yes_no(self, title, message, default_no=False):
        box = QMessageBox(self)
        box.setWindowIcon(get_app_icon())
        box.setWindowTitle(title)
        box.setText(message)
        box.setIcon(QMessageBox.Icon.Question)
        btn_yes = box.addButton(t("btn_yes"), QMessageBox.ButtonRole.YesRole)
        btn_no = box.addButton(t("btn_no"), QMessageBox.ButtonRole.NoRole)
        box.setDefaultButton(btn_no if default_no else btn_yes)
        box.exec()
        return box.clickedButton() == btn_yes

    def setup_ui(self):
        self._saved_chk_states = {}

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 28, 15, 15)
        main_layout.setSpacing(8)

        top_grid = QGridLayout()
        top_grid.setVerticalSpacing(8)
        top_grid.setHorizontalSpacing(15)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(t("search_placeholder"))
        self.search_input.setMinimumWidth(220)
        self.search_input.setFixedHeight(40)
        self.search_input.textChanged.connect(self.filter_tables)

        lang_layout = QHBoxLayout()
        lang_layout.setContentsMargins(0, 0, 0, 0)
        lang_layout.addWidget(QLabel(t("lbl_lang")))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(list(self.languages.keys()))
        self.lang_combo.currentTextChanged.connect(self.on_language_changed)
        self.lang_combo.setFixedHeight(40)
        self.lang_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lang_layout.addWidget(self.lang_combo)

        self.chk_hide_filenames = QCheckBox(t("chk_hide_filenames"))
        self.chk_hide_filenames.setChecked(get_hide_filenames())
        self.chk_hide_filenames.setFixedHeight(40)
        self.chk_hide_filenames.toggled.connect(self.on_filter_toggled)

        self.chk_hide_notfound = QCheckBox(t("chk_hide_notfound"))
        self.chk_hide_notfound.setChecked(get_hide_notfound())
        self.chk_hide_notfound.setFixedHeight(40)
        self.chk_hide_notfound.toggled.connect(self.on_filter_toggled)

        self.chk_hide_coop = QCheckBox(t("chk_hide_coop"))
        self.chk_hide_coop.setChecked(get_hide_coop())
        self.chk_hide_coop.setFixedHeight(40)
        self.chk_hide_coop.toggled.connect(self.on_filter_toggled)

        self.chk_hide_mission = QCheckBox(t("chk_hide_mission"))
        self.chk_hide_mission.setChecked(get_hide_mission())
        self.chk_hide_mission.setFixedHeight(40)
        self.chk_hide_mission.toggled.connect(self.on_filter_toggled)

        self.center_wrapper = QWidget()
        center_layout = QVBoxLayout(self.center_wrapper)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(2)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.expert_chk_container = QWidget()
        expert_chk_layout = QHBoxLayout(self.expert_chk_container)
        expert_chk_layout.setContentsMargins(0, 0, 0, 0)
        expert_chk_layout.setSpacing(20)
        expert_chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.chk_expand_all = QCheckBox(t("chk_expand_all"))
        self.chk_expand_all.setFixedHeight(25)
        self.chk_expand_all.toggled.connect(self.on_expand_all_toggled)
        
        self.chk_collapse_all = QCheckBox(t("chk_collapse_all"))
        self.chk_collapse_all.setFixedHeight(25)
        self.chk_collapse_all.toggled.connect(self.on_collapse_all_toggled)
        
        expert_chk_layout.addWidget(self.chk_expand_all)
        expert_chk_layout.addWidget(self.chk_collapse_all)

        self.expert_progress_container = QWidget()
        el = QHBoxLayout(self.expert_progress_container)
        el.setContentsMargins(0, 0, 0, 0)
        el.setSpacing(4)
        el.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.expert_spinner = QLabel("")
        self.expert_spinner.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        self.expert_spinner.setStyleSheet("color: #3498db; margin-bottom: 2px;")
        self.expert_spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.expert_progress = QProgressBar()
        self.expert_progress.setFixedWidth(180) 
        self.expert_progress.setFixedHeight(14)
        self.expert_progress.setTextVisible(False)
        
        el.addWidget(self.expert_spinner)
        el.addWidget(self.expert_progress)
        self.expert_progress_container.setVisible(False)
        
        center_layout.addWidget(self.expert_chk_container)
        center_layout.addWidget(self.expert_progress_container)

        self.btn_preload = QPushButton(t("btn_preload_ram"))
        self.btn_preload.setFixedHeight(40)
        self.btn_preload.setFixedWidth(220)
        self.btn_preload.setStyleSheet("background-color: #9b59b6; color: white; font-weight: bold; border-radius: 6px; border: none;")
        self.btn_preload.clicked.connect(self.preload_ram)
        self.btn_preload.setVisible(False)

        self.btn_zero_all = QPushButton()
        self.btn_zero_all.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 2px 14px;")
        self.btn_zero_all.setFixedHeight(40)
        self.btn_zero_all.setFixedWidth(220)
        
        balanced_text = self.get_balanced_text(self.btn_zero_all, t("btn_zero_special"), 220)
        self.btn_zero_all.setText(balanced_text)
        self.btn_zero_all.clicked.connect(self.zero_all_special_points)

        self.btn_mode = QPushButton("")
        self.btn_mode.setStyleSheet("font-weight: bold;")
        self.btn_mode.setFixedHeight(40)
        self.btn_mode.setFixedWidth(220)
        self.btn_mode.clicked.connect(self.toggle_mode)

        self.btn_open = QPushButton(t("btn_open"))
        self.btn_open.setFixedHeight(40)
        self.btn_open.setFixedWidth(220)
        self.btn_open.clicked.connect(self.open_rsdb_folder)

        self.btn_save = QPushButton(t("btn_save"))
        self.btn_save.setFixedHeight(40)
        self.btn_save.setFixedWidth(220)
        self.btn_save.clicked.connect(self.save_rsdb_folder)

        self.version_lbl = QLabel("")
        self.version_lbl.setStyleSheet("color: #EEEEEE; font-style: italic; font-weight: bold;")

        top_grid.addWidget(self.search_input, 0, 0)
        top_grid.addWidget(self.chk_hide_filenames, 0, 2)
        top_grid.addWidget(self.chk_hide_notfound, 0, 3)
        top_grid.addWidget(self.center_wrapper, 0, 2, 2, 2, Qt.AlignmentFlag.AlignCenter)
        top_grid.addWidget(self.btn_preload, 0, 5)
        top_grid.addWidget(self.btn_zero_all, 0, 5)
        top_grid.addWidget(self.btn_mode, 0, 6)

        top_grid.addLayout(lang_layout, 1, 0)
        top_grid.addWidget(self.chk_hide_coop, 1, 2)
        top_grid.addWidget(self.chk_hide_mission, 1, 3)
        top_grid.addWidget(self.btn_open, 1, 5)
        top_grid.addWidget(self.btn_save, 1, 6)

        top_grid.addWidget(self.version_lbl, 2, 5, 1, 2, Qt.AlignmentFlag.AlignRight)

        top_grid.setColumnStretch(0, 0)
        top_grid.setColumnStretch(1, 1) 
        top_grid.setColumnStretch(2, 0)
        top_grid.setColumnStretch(3, 0)
        top_grid.setColumnStretch(4, 1) 
        top_grid.setColumnStretch(5, 0)
        top_grid.setColumnStretch(6, 0)

        main_layout.addLayout(top_grid)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.left_frame = QFrame()
        self.left_frame.setObjectName("Card")
        left_panel_layout = QVBoxLayout(self.left_frame)
        left_panel_layout.setContentsMargins(10, 10, 10, 10)
        
        self.count_lbl = QLabel("")
        self.count_lbl.setObjectName("CountLabel")
        self.count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_panel_layout.addWidget(self.count_lbl)

        self.table_w = QTableWidget(0, 1)
        self.table_w.horizontalHeader().setStretchLastSection(True)
        self.table_w.horizontalHeader().hide()
        self.table_w.verticalHeader().hide()
        self.table_w.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_w.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_w.setShowGrid(False)
        self.table_w.setIconSize(QSize(28, 28))
        self.table_w.verticalHeader().setDefaultSectionSize(40)
        self.table_w.currentItemChanged.connect(self.on_table_current_changed)
        
        self.table_w.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_w.customContextMenuRequested.connect(self.on_table_context_menu)
        
        left_panel_layout.addWidget(self.table_w)
        
        self.btn_update = QPushButton(f"Splatoon 3 RSDB Editor (v{self.APP_VERSION})")
        self.btn_update.clicked.connect(self.launch_updater)
        left_panel_layout.addWidget(self.btn_update)
        
        self.btn_update.setIcon(QIcon())
        self.update_icon_overlay = QLabel(self.btn_update)
        self.update_icon_overlay.setFixedSize(24, 24)
        self.update_icon_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.update_icon_overlay.setStyleSheet("background: transparent;")
        self.btn_update.installEventFilter(self)
        
        self.splitter.addWidget(self.left_frame)

        self.right_frame = QFrame()
        self.right_frame.setObjectName("Card")
        right_layout = QVBoxLayout(self.right_frame)
        right_layout.setContentsMargins(20, 20, 20, 20)
        
        self.right_stack = QStackedWidget()
        self.right_stack.currentChanged.connect(lambda idx: self.update_action_buttons())
        
        self.tree_w = QTreeWidget()
        self.tree_w.setHeaderLabels([t("tree_prop"), t("tree_val")])
        self.tree_w.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tree_w.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree_w.setColumnWidth(0, 250)
        self.tree_w.setAlternatingRowColors(True)
        
        self.tree_w.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_w.customContextMenuRequested.connect(self.on_tree_context_menu)
        
        self.right_stack.addWidget(self.tree_w)
        
        self.easy_widget = QWidget()
        easy_layout = QVBoxLayout(self.easy_widget)
        easy_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        header_layout = QHBoxLayout()
        self.img_lbl = QLabel(t("img_unavail"))
        self.img_lbl.setFixedSize(128, 128)
        self.img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_lbl.setStyleSheet("border: 1px dashed rgba(128, 128, 128, 0.4); border-radius: 8px;")
        
        self.lbl_weapon_title = QLabel(t("lbl_weapon_name"))
        self.lbl_weapon_title.setStyleSheet("font-size: 18pt; font-weight: bold; margin-left: 15px;")
        self.lbl_weapon_title.setWordWrap(True)
        
        self.lbl_weapon_title.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lbl_weapon_title.customContextMenuRequested.connect(self.on_title_context_menu)
        
        header_layout.addWidget(self.img_lbl)
        header_layout.addWidget(self.lbl_weapon_title, 1)
        easy_layout.addLayout(header_layout)
        easy_layout.addSpacing(70)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(25)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft) 
        
        self.combo_sub = QComboBox()
        self.combo_sub.setFixedHeight(40)
        self.combo_sub.setIconSize(QSize(24, 24))
        self.combo_sub.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_sub.setMinimumContentsLength(10)
        self.combo_sub.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.combo_sub.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.combo_sub.customContextMenuRequested.connect(self.on_combo_sub_context_menu)
        
        self.combo_special = QComboBox()
        self.combo_special.setFixedHeight(40)
        self.combo_special.setIconSize(QSize(24, 24))
        self.combo_special.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_special.setMinimumContentsLength(10)
        self.combo_special.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.combo_special.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.combo_special.customContextMenuRequested.connect(self.on_combo_special_context_menu)
        
        self.spin_special_points = QLineEdit()
        self.spin_special_points.setFixedHeight(40)
        regex = QRegularExpression(r"^\d{1,12}$")
        self.spin_special_points.setValidator(QRegularExpressionValidator(regex))
        self.spin_special_points.setText("0")
        
        self.combo_sub.currentIndexChanged.connect(self.on_easy_form_changed)
        self.combo_special.currentIndexChanged.connect(self.on_easy_form_changed)
        self.spin_special_points.textChanged.connect(self.on_easy_form_changed)
        
        form_layout.addRow(t("lbl_sub_weapon"), self.combo_sub)
        form_layout.addRow(t("lbl_special_weapon"), self.combo_special)
        form_layout.addRow(t("lbl_special_points"), self.spin_special_points)
        
        easy_layout.addLayout(form_layout)
        self.right_stack.addWidget(self.easy_widget)
        
        right_layout.addWidget(self.right_stack)
        self.splitter.addWidget(self.right_frame)
        
        self.splitter.setSizes([380, 820])
        main_layout.addWidget(self.splitter, 1)
        
        self.combo_sub.installEventFilter(self)
        self.combo_special.installEventFilter(self)
        self.spin_special_points.installEventFilter(self)
        
        self.apply_mode()

    def manage_checkboxes_for_mode(self):
        easy_checkboxes = [
            self.chk_hide_filenames,
            self.chk_hide_notfound,
            self.chk_hide_coop,
            self.chk_hide_mission
        ]

        if not self.is_easy_mode: 
            for chk in easy_checkboxes:
                chk.setVisible(False)
                
            self.expert_progress_container.setVisible(False)
            self.expert_chk_container.setVisible(True)
        else: 
            self.expert_progress_container.setVisible(False)
            self.expert_chk_container.setVisible(False)
                
            for chk in easy_checkboxes:
                chk.setVisible(True)

    def apply_mode(self):
        self.manage_checkboxes_for_mode()
        
        self.btn_mode.setText(t('mode_expert') if self.is_easy_mode else t('mode_easy'))
        
        if self.is_easy_mode:
            self.right_stack.setCurrentIndex(1)
            self.table_w.setHorizontalHeaderLabels([t("table_header_weapons")])
        else:
            self.right_stack.setCurrentIndex(0)
            self.table_w.setHorizontalHeaderLabels([t("table_header_name")])
            
        self.update_action_buttons()
        self.refresh_left_panel()

    def setup_menus(self):
        self.top_bar = QWidget()
        self.top_bar.setObjectName("TopBar")
        self.top_bar.setStyleSheet("QWidget#TopBar { border-bottom: 1px solid rgba(0, 0, 0, 100); }")
        
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(3, 0, 15, 0) 
        top_layout.setSpacing(10)

        self._actual_menubar = QMenuBar()
        self._actual_menubar.setStyleSheet("QMenuBar { border-bottom: none; }") 
        self._actual_menubar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        
        file_menu = self._actual_menubar.addMenu(t("menu_file"))
        reset_action = QAction(t("menu_reset"), self)
        reset_action.triggered.connect(self.reset_config_and_restart)
        file_menu.addAction(reset_action)
        
        help_menu = self._actual_menubar.addMenu(t("menu_help"))
        about_action = QAction(t("menu_about"), self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
        
        top_layout.addWidget(self._actual_menubar)
        
        self.btn_we = QPushButton(t("btn_we")) 
        self.btn_we.clicked.connect(self.show_we_notice)
        self.btn_we.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_we.setFixedHeight(26) 
        self.btn_we.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; font-weight: bold; font-size: 10pt; border-radius: 4px; border: 1px solid #1e8449; padding: 0px 15px; }
            QPushButton:hover { background-color: #1e8449; }
        """)
        
        top_layout.addWidget(self.btn_we, alignment=Qt.AlignmentFlag.AlignVCenter)
        top_layout.addStretch()
        
        self.setMenuWidget(self.top_bar)

    def ui_update_texts(self):
        self.setWindowTitle(t("window_title"))
        self.btn_open.setText(t("btn_open"))
        self.btn_save.setText(t("btn_save"))
        self.chk_hide_filenames.setText(t("chk_hide_filenames"))
        self.chk_hide_coop.setText(t("chk_hide_coop"))
        self.chk_hide_mission.setText(t("chk_hide_mission"))
        self.chk_hide_notfound.setText(t("chk_hide_notfound"))
        self.chk_expand_all.setText(t("chk_expand_all"))
        self.chk_collapse_all.setText(t("chk_collapse_all"))
        self.search_input.setPlaceholderText(t("search_placeholder"))
        self.btn_we.setText(t("btn_we"))
        self.btn_preload.setText(t("btn_preload_ram"))
        
        balanced_text = self.get_balanced_text(self.btn_zero_all, t("btn_zero_special"), 220)
        self.btn_zero_all.setText(balanced_text)
        
        self.btn_mode.setText(t('mode_expert') if self.is_easy_mode else t('mode_easy'))
        
        if self.is_easy_mode:
            self.table_w.setHorizontalHeaderLabels([t("table_header_weapons")])
        else:
            self.table_w.setHorizontalHeaderLabels([t("table_header_name")])

        if hasattr(self, '_last_total'):
            current_row = 0
            if self.table_w.currentItem():
                current_row = self.table_w.currentItem().row() + 1
            self.count_lbl.setText(t("count_info", getattr(self, '_last_total', 0), getattr(self, '_last_displayed', 0), current_row, getattr(self, '_last_displayed', 0)))
        else:
            self.count_lbl.setText(t("count_info", 0, 0, 0, 0))

    def show_about_dialog(self):
        dialog = AboutDialog(self, darkdetect.isDark(), self.APP_VERSION)
        dialog.exec()