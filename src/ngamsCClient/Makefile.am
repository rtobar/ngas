AUTOMAKE_OPTIONS = 1.8 foreign
DISTCLEANFILES = *~

# The initial library
lib_LTLIBRARIES = libngams.la
libngams_la_LDFLAGS = -version-info $(LT_CURRENT):$(LT_REVISION):$(LT_AGE)
libngams_la_SOURCES = \
		ngamsCClientLib.c \
		ngamsARCH_CLI_MAN_PAGE.c \
		ngamsLICENSE.c \
		ngamsMAN_PAGE.c \
		ngamsMAN_PAGE_X.c

# Individual programs and their dependencies
bin_PROGRAMS =  ngamsCClient ngamsCClientX ngamsArchiveClient ngamsCrc32

ngamsCClient_SOURCES = ngamsCClient.c
ngamsCClient_LDADD = libngams.la

ngamsCClientX_SOURCES = ngamsCClientX.c
ngamsCClientX_LDADD = libngams.la

ngamsArchiveClient_SOURCES = ngamsArchiveClient.c
ngamsArchiveClient_LDADD = libngams.la

ngamsCrc32_SOURCES = ngamsCrc32.c
ngamsCrc32_LDFLAGS = -lz

# Files to be installed under <prefix>/include
include_HEADERS = ngams.h

# Files not to be installed under <prefix>/include, but to be added to the
# distribution
noinst_HEADERS = ngamsArchiveClient.h

EXTRA_DIST = ngamsArchiveClient.doc ngamsCClientX.doc

ngamsCClientLib.c: ngamsVERSION.h

ngamsLICENSE.c:
	@-(rm -f ngamsLICENSE.c)
	@-(echo  "#include <string.h>" > ngamsLICENSE.c)
	@-(echo  "#include \"ngams.h\"" >> ngamsLICENSE.c)
	@-(echo  "char *_ngamsLicense(void)" >> ngamsLICENSE.c)
	@-(echo  "{" >> ngamsLICENSE.c)
	@-(echo  "static char buf[32768];" >> ngamsLICENSE.c)
	@-(echo  "char *txt[] = {" >> ngamsLICENSE.c)
	@-(awk -f ngamsFormatHdrFile.awk ../../LICENSE >> ngamsLICENSE.c)
	@-(echo  "\"*\"};" >> ngamsLICENSE.c)
	@-(echo  "int n;" >> ngamsLICENSE.c)
	@-(echo  "for (n = 0; *txt[n] != '*'; n++) {strcat(buf, txt[n]); strcat(buf, ngamsNEWLINE);}" >> ngamsLICENSE.c)
	@-(echo  "return buf;" >> ngamsLICENSE.c)
	@-(echo  "}" >> ngamsLICENSE.c)

ngamsMAN_PAGE.c:
	@-(rm -f ngamsMAN_PAGE.c)
	@-(echo  "#include <string.h>" > ngamsMAN_PAGE.c)
	@-(echo  "#include \"ngams.h\"" >> ngamsMAN_PAGE.c)
	@-(echo  "char *_ngamsManPage(void)" >> ngamsMAN_PAGE.c)
	@-(echo  "{" >> ngamsMAN_PAGE.c)
	@-(echo  "static char buf[32768];" >> ngamsMAN_PAGE.c)
	@-(echo  "char *txt[] = {" >> ngamsMAN_PAGE.c)
	@-(awk -f ngamsFormatHdrFile.awk ../ngamsPClient/ngamsPClient/doc/ngamsPClient.txt >> ngamsMAN_PAGE.c)
	@-(echo  "\"*\"};" >> ngamsMAN_PAGE.c)
	@-(echo  "int n;" >> ngamsMAN_PAGE.c)
	@-(echo  "for (n = 0; *txt[n] != '*'; n++) {strcat(buf, txt[n]); strcat(buf, ngamsNEWLINE);}" >> ngamsMAN_PAGE.c)
	@-(echo  "return buf;" >> ngamsMAN_PAGE.c)
	@-(echo  "}" >> ngamsMAN_PAGE.c)

ngamsMAN_PAGE_X.c:
	@-(rm -f ngamsMAN_PAGE_X.c)
	@-(echo  "#include <string.h>" > ngamsMAN_PAGE_X.c)
	@-(echo  "#include \"ngams.h\"" >> ngamsMAN_PAGE_X.c)
	@-(echo  "char *_ngamsManPageX(void)" >> ngamsMAN_PAGE_X.c)
	@-(echo  "{" >> ngamsMAN_PAGE_X.c)
	@-(echo  "static char buf[32768];" >> ngamsMAN_PAGE_X.c)
	@-(echo  "char *txt[] = {" >> ngamsMAN_PAGE_X.c)
	@-(awk -f ngamsFormatHdrFile.awk ngamsCClientX.doc >> ngamsMAN_PAGE_X.c)
	@-(echo  "\"*\"};" >> ngamsMAN_PAGE_X.c)
	@-(echo  "int n;" >> ngamsMAN_PAGE_X.c)
	@-(echo  "for (n = 0; *txt[n] != '*'; n++) {strcat(buf, txt[n]); strcat(buf, ngamsNEWLINE);}" >> ngamsMAN_PAGE_X.c)
	@-(echo  "return buf;" >> ngamsMAN_PAGE_X.c)
	@-(echo  "}" >> ngamsMAN_PAGE_X.c)

ngamsARCH_CLI_MAN_PAGE.c:
	@-(rm -f ngamsARCH_CLI_MAN_PAGE.c)
	@-(echo  "#include <string.h>" > ngamsARCH_CLI_MAN_PAGE.c)
	@-(echo  "#include \"ngams.h\"" >> ngamsARCH_CLI_MAN_PAGE.c)
	@-(echo  "char *ngamsArchCliManPage(void)" >> ngamsARCH_CLI_MAN_PAGE.c)
	@-(echo  "{" >> ngamsARCH_CLI_MAN_PAGE.c)
	@-(echo  "static char buf[32768];" >> ngamsARCH_CLI_MAN_PAGE.c)
	@-(echo  "char *txt[] = {" >> ngamsARCH_CLI_MAN_PAGE.c)
	@-(awk -f ngamsFormatHdrFile.awk ngamsArchiveClient.doc >> ngamsARCH_CLI_MAN_PAGE.c)
	@-(echo  "\"*\"};" >> ngamsARCH_CLI_MAN_PAGE.c)
	@-(echo  "int n;" >> ngamsARCH_CLI_MAN_PAGE.c)
	@-(echo  "for (n = 0; *txt[n] != '*'; n++) {strcat(buf, txt[n]); strcat(buf, ngamsNEWLINE);}" >> ngamsARCH_CLI_MAN_PAGE.c)
	@-(echo  "return buf;" >> ngamsARCH_CLI_MAN_PAGE.c)
	@-(echo  "}" >> ngamsARCH_CLI_MAN_PAGE.c)

ngamsVERSION.h:
	@-(rm -f ngamsVERSION.h)
	@-(cat ../../VERSION > ngamsVERSION.h)

CLEANFILES= ngamsVERSION.h ngamsARCH_CLI_MAN_PAGE.c ngamsMAN_PAGE.c ngamsLICENSE.c

# Files to be removed with command: make maintainer-clean
MAINTAINERCLEANFILES = Makefile.in aclocal.m4 config.h.in config.log \
        config.status configure stamp-h.in configure.scan autoscan.log \
        admin/config.guess admin/config.sub admin/depcomp admin/install-sh \
        admin/ltmain.sh admin/missing

# EOF
