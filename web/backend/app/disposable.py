"""
Disposable email domains — reject registrations from known temporary email providers.

List curated from multiple public sources. Add more as needed.
"""

_RAW = """
0-mail.com 0815.ru 0wnd.net 0wnd.org 10mail.org 10minutemail.com 20mail.eu 20mail.in
20mail.it 20minutemail.com 2ch.computer 2prong.com 3d-painting.com 3trtretgfrfe.net 4mail.cf
4mail.ga 4warding.com 4warding.net 4warding.org 60minutemail.com 675hosting.com
675hosting.net 675hosting.org 6ip.us 6paq.com 6url.com 75hosting.com 75hosting.net
75hosting.org 7tags.com 8chan.co 8mail.cf 8mail.ga 8mail.ml 9ox.net a-bc.net
abandoned.email abyssmail.com afrobacon.com ajaxapp.net akorde.al amail.com
amilegit.com amiri.net amiriindustries.com anappthat.com anonymized.org anonymousspeech.com
antichef.com antichef.net antireg.com antireg.ru antonelli.cheap ay33rs.flu.cc
b.cr.cloudns.asia backflip.cf backflip.ws baxomale.htsail.com belljonestax.com
belisim.we.bs bigprofessor.so binsource.we.bs biskvitt.tk bitwerke.com bloatbox.com
blogmyway.org bobmail.info bodhi.lawlita.com bofthew.com boun.cr boun.ws boximail.com
boxomail.live brefmail.com broadbandninja.com bumpymail.com bund.us burnthebook.com
buydfcatssnapbacks.xyz buyordie.info byom.de c.hcac.net c2.hu cachislaw.we.bs
canned.me car101.pro cartelera.org casio.host cc.liamria cenkk.com ch.tc chacuo.net
cheaphub.net cheshmeh.info ckiso.com cl-cl.org clinchem.com clonemoi.tk cloudns.asia
clphillips.we.bs clrmail.com cmail.club codivide.com comparatif.net complejidad.org
consumerriot.com contbay.com cool.fr.nf coolandwacky.us cordlessdog.com crydeck.com
cue3.com curio24.no cust.in cuvox.de d3p.dk daabox.com dacoolest.com damnthespam.com
dayrep.com dbunker.com deadaddress.com deadspam.com deagot.com dealja.com delikkt.de
despam.it despammed.com devnullmail.com dfgh.net digdy.com discard.email
discardmail.com discardmail.de disign-concept.eu disign-realm.com dispostable.com
dk3.com dodsi.com doktor-info.de domain1qlhidba2nz0z.online domain1t8nxrqki1nq.online
domozmail.com donnar.it dontreg.com dontsendmespam.de dotman.de doy.kim drnetwork.org
dropmail.me duam.net dudmail.com dump-email.info dumpmail.de dumpyemail.com
dvd.dns-cloud.net dvd.dnsabr.com dx.ez.lv dxtt.org e-mail.com e-mail.org e4ward.com
easytrashmail.com edfvntmd.com einrot.com einrot.de eluvit.com email-temp.com
emailgo.de emailias.com emailna.co emeraldwebmail.com emil.com emkei.cf emkei.ga
emkei.ml emkei.tk ephemail.net eqvibes.studio est.une.victime.ninja etranquil.com
etranquil.net etranquil.org evanferm.wideofilmowanie.com fake-box.com fakeinbox.com
fakeinformation.com fastacura.com fastchevy.com fasttoyota.com fbi.com.co fbmail.com.mx
ficken.de fightallspam.com fiifke.de filzmail.com fizmail.com fly-ts.de
flyspam.com frappina.com free-email.one freebabysittercam.com
freebullets.net freecoolemail.com freefattymovies.com freehotmail.net
freeinbox.email freelollipop.com freemailsrv.info freenetjazz.com freeprice.co
freeweb.email fressse.net friendlymail.co.uk front14.org fuglu.com
fuckingduh.com fudgerub.com fun64.com fun64.net fuvk.ru fw.moza.pl
fxprix.com garbagemail.org gardenscape.ca gav0.com get-mail.cf get-mail.ga
get-mail.ml get2is.com getairmail.com getmails.eu getonemail.com getonemail.net
ghosttexter.de giantmail.de girlmail.win gishpuppy.com givmail.com gixenmixen.tk
glubex.com gmial.com goosebox.com great-host.in greensloth.com grr.la
gs-arc.org gsrv.co.uk gstpub.biz guerillamail.com guerrillamail.biz
guerrillamail.com guerrillamail.de guerrillamail.info guerrillamail.net
guerrillamail.org guerrillamailblock.com gustr.com gynzi.com h.mintemail.com
h8s.org hackthatbit.com hahados.be happysinner.sytes.net harakirimail.com
hat-geld.de hatespam.org herbalshtabashop.xyz herpderp.nl hetnieuwejournaal.info
hi5.si hiddentragedy.com hidemail.de hidzz.com hitbts.com hmail.us ho3.com
hockeymail.us hopoverview.com hotmail.ms hotpop.com htelcs.com hulapla.de
humaility.com i2pmail.org icecreamtest.com ichichich.com ieatcats.org igcl.com
ihateyoualot.info ihazspam.ca iheartspam.org ikbenspamvrij.nl imails.info
imgof.com imgv.de inboxalias.com inboxclean.com inboxclean.org inboxdesign.me
inboxed.im inboxed.pw inboxkitten.com inboxproxy.com incest247.biz
inclusiveprogress.com incognitomail.com incognitomail.net incognitomail.org
insanumingenium.info installhos.bid instruction.giantwords.de inzamba.co.za
iochk.com ip6.li iravan.com iscam.tk it-italy.info ixkx.net ixx.io iyukg.com
jcpclothing.agency jkevey.ltd jobpost.consulting jopho.com jourrapide.com
jsrsolutions.com junk.to junk1e.com junkmail.com junkmail.gq junkmail.works
justemail.ml k.fido.be kasmail.com kaspop.com keepmymail.com killmail.com
killmail.net kilocycl.es kir.ch.tc kittiza.com kinzaprint.co kismail.com
klassmaster.com klassmaster.net kloap.com klzlk.com kosmetika-24.com
koszmail.pl krdservices.com ktumail.online kubuu.online
kuku.lu kz.app l33r.com lackmail.net lackmail.ru lacto.info
lags.us lal.kr landmail.co laoeq.com lasix.site last-chance.pro
lavabit.com lawlita.com lazyinbox.com leeching.net letmeinonthis.com
letthemeatspam.com lgfvh9hdvqwx8.com liefs.com lifebyfood.com
link2mail.net litedrop.com loadby.us loan101.pro locanto.club locawire.com
lordvold.cf lordvold.tk lortemail.dk lovesea.gq lr7.us lr78.com luckymail.com
lukecarriere.com lukop.dk lupabap.com lusianimo.com.ly lzoaq.com
m.ddcrew.com m21.cc m4ilweb.info maboard.com macr2.com mail-card.net mail-awu.de
mail-easy.fr mail-filter.com mail-finder.net mail-me.com mail-owl.com
mail-temporaire.com mail-temporaire.fr mail.by mail.wtf mail0.ga mail114.net
mail1a.de mail21.cc mail22.club mail2rss.org mail4trash.com mail666.ru
mail75.club mailbiz.biz mailblocks.com mailbox52.ga mailbox72.biz
mailbox80.biz mailbox87.de mailbox92.biz mailbucket.org mailcat.biz mailcatch.com
mailde.de mailde.info maildrop.cc maildu.de maildx.com maileater.com
mailexpire.com mailfa.tk mailforspam.com mailfree.ga mailfree.gq mailfree.ml
mailfreeonline.com mailfs.com mailguard.me mailhazard.com mailhazard.us
mailhz.me mailimate.com mailin8r.com mailinatar.com mailinater.com
mailinator.com mailinator.net mailinator.org mailinator.us mailinator0.com
mailinator1.com mailinator2.com mailinator3.com mailinator4.com mailinator5.com
mailinator6.com mailinator7.com mailinator8.com mailinator9.com mailincubator.com
mailismagic.com mailita.tk mailjunk.cf mailjunk.ga mailjunk.gq mailjunk.ml
mailjunk.tk mailmate.com mailme24.com mailmenow.biz mailmetrash.com
mailmoat.com mailmoth.com mailms.com mailna.biz mailna.co mailna.in
mailna.me mailnator.com mailnesia.com mailnull.com mailonaut.com
mailorc.com mailorg.org mailox.fun mailpick.biz mailproxsy.com
mailquack.com mailrock.biz mailsac.com mailscrap.com mailseal.de
mailshell.com mailsiphon.com mailslapping.com mailslite.com mailsucker.net
mailtemp.info mailtemporaire.com mailtemporaire.fr mailtome.de mailtothis.com
mailtrap.io mailtrash.net mailtv.net mailtv.tv mailwithyou.com mailzilla.com
mailzilla.org mainerfolg.info makemenaughty.net makemetheking.com
malahov.de manifestgenerator.com mansker.net manybrain.com markmurfin.com
mastr.com.mk mbstudio.com.ua mcbane.ga medsheet.com mega.zik.dj meinspamschutz.de
mentally-ill-guardian.ga mentornetz.org messagebeamer.de mewandyq.xyz
mezimages.net mfsa.ru miam.kd2.org microwavetechnologies.com midcoastcustoms.net
midcoastsolutions.com migmail.net migmail.pl migumail.com mikrotamanet.com
mintemail.com miraclegifts.com mjukglass.nu moakt.co moakt.ws moburl.com
mohmal.com molms.com momentics.ru monkeywithawinner.net monsterjcy.pw
montepaone.one moonrankgtmyatr.shop mornet.ca moruzza.com
motique.de mspeciosa.com mswork.ru mt2009.com mt2014.com mt2015.com
mubuy.ml muehlacker.tk muqwftsjuatxw.biz mutant.me mvrht.com
mvrht.net mwarrior.org mxd.trillianx.com mxp.dnsabr.com
my10minutemail.com mybitti.de mycard.net.ua mycleaninbox.net
myemailboxy.com myindohome.services mynetstore.de mypackme.com
mypartyclip.de myphantomemail.com mysamp.de myspaceinc.com
myspaceinc.net myspaceinc.org myspacepimpedup.com myspamless.com
mystvpn.com mytemp.email mytempmail.com mytrashmail.com nachoca.com
nada.email nada.ltd naftel.net nagi.be nasset.pl negative-ions.net
neko2.net netmail3.net netzidiot.de neverbox.com nice-4u.com nincsmail.com
nincsmail.hu niromail.com nnh.com no-spam.ws nobleglobal.com noblepioneer.com
nobuma.com noclickemail.com noicd.com noiuih.com nolog.net.ua nonspam.eu
nonspammer.de noref.in notmailinator.com notrnailinator.com nowmymail.com
nowsafe.com ntosr.com nullbox.info nur-fuer-spam.de nutpa.net
nwldx.com nwytg.net nwytg.net o.spamtrap.ro o3enzyme.com oalsp.com
objectmail.com obobbo.com oepia.com ohdomain.xyz ohmyfly.com
oida.de oktricks.com omani.ga one-time.email one2mail.info
oneoffemail.com oneoffmail.com oosln.com opayq.com opentrash.com
opposir.com orange-bonobo.com ordinaryamerican.net osakawiduerr.cf
oshietechan.link otherinbox.com ourklips.com outcazli.polishmasturbation.com
outlawspam.com ov3u841.com owlpic.com p3heg.com p71ce1m.com
pagamenti.tk pancakemail.com paplease.com paranoiatrip.com
pcusers.otherinbox.com pedimed-szczecin.pl penpaland.com pepbot.com
pflznq.ooo pimpedupmyspace.com pineoilriglay.com
pjjkp.com plasson.org plecks.tk plhk.ru ploae.com plw.me
pojok.ml politicatarian.com politikerclub.de polynom-trading.com
pooae.com poppymail.kro.kr porsh.net posta.xyz postonline.me
powerlink.com.np pp.ua preventmideyelashes.info prixfixe.net
privacymailshh.xyz privy-mail.com privy-mail.de privymail.de
procrackers.com prodelvalle.com proinbox.com protection-0.xyz
proxymail.eu prtnx.com prtshr.com psoxs.com pubwarez.com
puk.us.to pulpwax.com purcell.email purelogistics.org pushmojo.com
put2.net putthisinyourspamdb.com pw.epac.to qbqso.com qisdo.com
qisoa.com quickmail.nl ququb.com qwfox.com r4nd0m.de raetp9.com
raketenmann.de rancidhome.net randomail.net rapamovic.cf
rcpt.at reallymymail.com realtyalerts.ca rebatesstream.com
receiveee.com recipeforfailure.com recyclemail.dk reddit.usa.cc
redfeathercrow.com regbypass.com regbypass.comsafe-mail.net
rejectmail.com remail.cf remail.ga renraku.in
resigorena.buzz rhyta.com rklips.com rma.ec rnwk.xyz
rollindo.agency roscorportals.me rotaniliam.com rowe-solutions.com
royal.net royalweb.email rppkn.com rtrtr.com
rudiplo.ru ruffrey.com runi.ca rusty-dog.com s0ny.net
s33db0x.com sabrestlouis.com sackboii.com
safe-mail.net safersignup.de safetymail.info safetypost.de
sandelf.de saynotospams.com schafmail.de schmeissweg.tk
schrott-email.de sdg3456yer.ga secretemail.de
secure-mail.biz secure-mail.cc secured-link.net
seekapps.com selfdestructingmail.com selfdestructingmail.org
sendspamhere.com senseless-entertainment.com server.ms
services391.com shanedo.com sharedmailbox.org sharklasers.com
shieldemail.com shieldemails.com shiftmail.com
shipfromto.com shit.dns-cloud.net shit.dnsabr.com
shitmail.de shitmail.me shitmail.org shitware.nl
shmeriously.com shopxda.com shortmail.net shotmail.ru
showslow.de sibmail.com sikomo.com simpleitsecurity.info
sink.fblay.com siteposter.net six6.nl sixtpt.com
sizzlemctwizzle.com skeefmail.com skrak.com
skrx.tk skyrt.de slapsfromlastnight.com
slippery.email slipry.net slotter.com slowslow.de
sluteen.com sluteen.info slutmom.info
smashmail.de smellfear.com smellrear.com
snakemail.com sneakemail.com sneakmail.de
snkmail.com socialfurry.org sofimail.com
sofort-mail.de softpls.asia sogetthis.com
sohu.net soisz.com solvemail.info
sonshi.cf soon.com soseducation.org
spa.com spam-en.de spam.care spam.coroiu.com
spam.2012-2016.ru spam.dnsabr.com spam.la spam.netpul.se
spam.su spam4.me spamail.de spamany.com spamavert.com
spambob.com spambob.net spambob.org spambog.com
spambog.de spambog.net spambog.ru spambox.info
spambox.me spambox.org spambox.us spamcannon.com
spamcannon.net spamcero.com spamcon.org spamcorptastic.com
spamcowboy.com spamcowboy.net spamcowboy.org
spamday.com spamdecoy.net spamex.com spamfighter.cf
spamfighter.ga spamfighter.gq spamfighter.ml spamfighter.tk
spamfree.eu spamfree24.com spamfree24.de spamfree24.eu
spamfree24.info spamfree24.net spamfree24.org
spamgoes.in spamgourmet.com spamgourmet.net spamgourmet.org
spamherelots.com spamhereplease.com spamhole.com spamify.com
spaminator.de spamkill.info spaml.com spaml.de spammer.fail
spamobox.com spamoff.de spamoff.info spamsalad.in
spamserver.cf spamserver.ml spamserver.tk spamspot.com
spamstack.net spamthis.co.uk spamthisplease.com
spamtrail.com spamtrail.com spamtrap.ro
spamwc.cf spamwc.ga spamwc.gq spamwc.ml
speedgaus.net speerpwo.com sperma.cf
spikio.com spindl-e.com sportrid.com
spybox.de ssoia.com startkeys.com
stexsy.com stinkefinger.net stop-my-spam.cf
stop-my-spam.ga stop-my-spam.ml stop-my-spam.tk
streerd.com stressthebeast.site stromox.com
stuffmail.de super-auswahl.de supergreatmail.com
supermailer.jp superrito.com supersave.net
suremail.info svk.jp sweetxxx.de
t.woeishyang.com tafmail.com taglead.com
talkinator.com tapchicuoihoi.com tarhely.xyz
tb-on-line.net techemail.com technoproxy.com
teerest.com teewars.org telekgaring.cf
teleworm.com teleworm.us tellos.xyz
temp-mail.com temp-mail.de temp-mail.info
temp-mail.io temp-mail.net temp-mail.org
temp-mail.ru temp.emeraldwebmail.com
temp.headstrong.de temp.maildemise.com
temp1.club temp15qm.com temp2.club
tempail.com tempalias.com tempcloud.info
tempemail.biz tempemail.co tempemail.co.za
tempemail.com tempe-mail.com tempemail.net
tempemail.pro tempinbox.co.uk tempinbox.com
tempmail.com tempmail.de tempmail.eu
tempmail.it tempmail.pro tempmail.us
tempmail.ws tempmail2.com tempmaildemo.com
tempmailer.com tempmailer.de tempmails.org
tempomail.fr tempomail.org temporarily.de
temporalmail.com temporarily.de temporarioemail.com.br
temporary-mail.host temporaryemail.net temporaryemail.us
temporaryinbox.com temporarymailaddress.com tempr.email
tempsky.com tempthe.net tempymail.com testore.co
thanksnospam.info thankyou2010.com thatim.info
thc.st thietbiagay.com thisisnotmyrealemail.com
thismail.net throwaway.email throwawayemailaddress.com
throwawaymail.com thu.tf tittbit.in tizi.com
toi.kr toiea.com top101.de top1mail.ru
top1post.ru topofertasdehoje.com topranklist.de
tormail.org tqoai.com tradermail.info
trash-amil.com trash-mail.at trash-mail.cf
trash-mail.com trash-mail.de trash-mail.ga
trash-mail.gq trash-mail.ml trash-mail.tk
trash-me.com trash2009.com trash2010.com
trash2011.com trashcanmail.com trashdevil.com
trashdevil.de trashemail.de trashimail.de
trashinbox.com trashmail.at trashmail.com
trashmail.de trashmail.gq trashmail.io
trashmail.me trashmail.net trashmail.org
trashmail.ws trashmailer.com trashymail.com
trashymail.net trayna.com trbvm.com
trbvn.com trbvo.com trendline-sport.com
trialmail.de trickmail.net trillianpro.com
trimsj.com tryalert.com tryninja.io
turuma.info turoid.com tvimail.com
twinmail.de twoweeksextrem.de uacro.com
ualmail.com ubergroceries.com ubismail.net
uggsrock.com ujijima1129.gq uliza.net
umail.net undo.it unicredit.co.bw unids.com
unimark.org unit7lahaina.com
unlimit.com upliftnow.com uplipht.com
uploadnolimit.com uqjglpzrwa.gq
uralplay.ru urfunge.se
uroid.com us.af utiket.us uzrip.com
v0nly.one vaffanculo.gq valemail.net
vanacken.agency vercelli.cf vercelli.ga
vercelli.gq vercelli.ml verifrom.ml
veryrealemail.com vidchart.com viditag.com
viewcastmedia.com viewcastmedia.net
viewcastmedia.org virgilio.it
virtual-email.com viuzza.net
vkje.xyz vmail.me vmailing.info
vmani.com void.maride.cc voidbay.com
voltaer.com vomoto.com vpn.st
vps30.com vradportal.com
vsimcard.com vssms.com
vubby.com vui.pub vzti.com
w4i.eml.cc w9y9640c.static.otenet.gr
walkmail.net walkmail.ru wasteland.rfc822.org
watch-harry-potter.com watchever.biz watchfull.net
watchironman3onlinefreefullmovie.com
wazabi.club web-contact.info web.id
web2mailco.com webcontact-france.eu
webm4il.info webmail24.info
webmails.info weg-werf-email.de
wegwerf-email.at wegwerf-email.de
wegwerf-email.net wegwerf-email.org
wegwerf-emailadresse.com wegwerf-emails.at
wegwerfadresse.de wegwerfemail.com
wegwerfemail.de wegwerfemail.info
wegwerfemail.net wegwerfemail.org
wegwerfmail.de wegwerfmail.info
wegwerfmail.net wegwerfmail.org
wegwerpmailadres.nl wetrainbayarea.com
wetrainbayarea.org wh4f.org
whatiaas.com whatifknockknock.com
whatpaas.com whatsaas.com
whiffles.org whopy.com
whtjddn.nonejar.com wibuw.flu.cc
widesawlic.com wilemail.com
willhackforfood.biz willselfdestruct.com
winemaven.info wins.com.br
wizdom.xyz wizdomshop.cc
wmail.cf wolfsmail.tk
worm4u.info wornadobe.info
wovenso.com wow.royalbrand.click
wpkg.de wpg.im wralawfirm.com
writeme.us wronghead.com
wuzup.net wuzupmail.net
wwjmp.com www.bccto.me www.e4ward.com
www.gishpuppy.com www.mailinator.com
wwweb.com x.ip6.li x1x.spb.ru
x1x22716.com x24.com xagloo.co
xagloo.com xcode.ro xemaps.com
xents.com xjoi.com xkx.me
xl.cx xmail.com xmaily.com
xn--9kq967o.com xoixa.com
xost.us xoxy.net xperiae5.info
xrho.com xsmail.com
xtream-solutions.com
xtream-solutions.net xuwphq.tech
xvx.us xwaretech.com
xwaretech.info xww.ro
xxhamsterxx.ga xxyy.ro
xyzfree.net xzsok.com
yalta.krim.ws yandex.com
yapped.net yeah.net
yep.it ymail.net
yogamaven.com yomail.info
yopmail.com yopmail.fr
yopmail.gq yopmail.net
yopmail.pp.ua yordanmail.cf
you-spam.com youatyourservice.com
yourlms.biz ypmail.webarnak.fr.eu.org
yroid.com yuurok.com
yytv.ddns.info z0d.eu
z86.ru zaktouni.fr
zebins.com zebins.eu
zehnminuten.de zehnminutenmail.de
zenmo.ru zephyrus.digital
zepp.dk zetmail.com
zfymail.com zhaohishu.com
zhas.loan zhas.men zhaunpengyuan.vip
zhcne.com zhewei88.com zhongchengtz.com
zik.dj zippy.life zipzaps.de
ziyap.com zkte.com zl0irl.com
zmail.info.pl zomg.info
zoomasdnklq.loan zoomku.com
zoxtdn.com zua981.com zuberka.com
zumpul.com zx81.ovh zxcv.com
zxcvbnm.com zyns.com zzz.com
"""

DISPOSABLE_DOMAINS: set[str] = set()

def _init():
    """Lazily build the set on first access."""
    if DISPOSABLE_DOMAINS:
        return
    for line in _RAW.splitlines():
        line = line.strip()
        if not line:
            continue
        # Extract domain from each token (some lines have multiple)
        for token in line.split():
            token = token.strip().lower()
            if '.' in token and not token.startswith('*'):
                DISPOSABLE_DOMAINS.add(token)

_init()


def is_disposable_email(email: str) -> bool:
    """Check if an email address uses a known disposable domain."""
    try:
        domain = email.strip().lower().split('@', 1)[1]
    except (IndexError, ValueError):
        return True
    return domain in DISPOSABLE_DOMAINS


def valid_email_pattern(email: str) -> bool:
    """Basic email format validation."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))
