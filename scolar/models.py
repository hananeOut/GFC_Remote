from django.db import models
from django.db.models.deletion import CASCADE
from django.core.validators import RegexValidator
from django.db import transaction
from django.urls import reverse
from django.contrib.auth.models import AbstractUser
from django.db.models.fields import CharField
import decimal
from django.db.models import Q, F, Count, ExpressionWrapper, DecimalField, Avg, Max, Min, Sum
import datetime
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import Group
from random import randint
from django.core.exceptions import ValidationError
import re
from djmoney.models.fields import MoneyField

from django.template.defaultfilters import default

class User(AbstractUser):
    REQUIRED_FIELDS = ['email']
    email = models.EmailField(
        verbose_name=("email address"), unique=True,
        error_messages={
            'unique': (
                "A user is already registered with this email address"),
        },
    )
    
    def institution(self):
        institution_ = Institution.objects.all()
        if institution_.exists():
            institution_=institution_[0]
        else :
            institution_ = Institution.objects.create(nom='Ecole nationale Supérieure d\'Informatique', 
                                                      nom_a='المدرسة الوطنية العليا للإعلام الآلي',
                                                      sigle='ESI',
                                                      ville='Oued Smar',
                                                      ville_a='‫واد سمار‬',
                                                      adresse='BPM68 16270, OUed Smar, Alger',
                                                      tel='023939132', 
                                                      fax='023939142',
                                                      web='http://www.esi.dz',
                                                      )
            institution_.banniere.name = institution_.banniere.field.upload_to+'/banniere.png'
            institution_.logo.name = institution_.logo.field.upload_to+'/ESI_Logo.png'
            institution_.logo_bis.name = institution_.logo_bis.field.upload_to+'/Logo_ESI_talents.png'
            institution_.header.name =institution_.header.field.upload_to+'/Entete_ESI_lg.png'
            institution_.footer.name =institution_.footer.field.upload_to+'/Foot_ESI_lg.png'
            institution_.illustration_cursus.name =institution_.illustration_cursus.field.upload_to+'/etudes_esi.png'
            institution_.save()
        return institution_
        
    def nom(self):
        if self.is_enseignant():
            return self.enseignant.nom
        elif self.is_etudiant():
            return self.etudiant.nom
        elif self.is_personnel():
            return self.personnel.nom
        else:
            return str(self)

    def prenom(self):
        if self.is_enseignant():
            return self.enseignant.prenom
        elif self.is_etudiant():
            return self.etudiant.prenom
        elif self.is_personnel():
            return self.personnel.prenom
        else:
            return str(self)
    
    def annee_encours(self):
        return AnneeUniv.objects.get(encours=True)
    
    def inscription_encours_list(self):
        if self.is_etudiant():
            return Inscription.objects.filter(etudiant=self.etudiant, formation__annee_univ__encours=True)
        else:
            return Inscription.objects.none()

    def is_top_management(self):
        group_admin=get_object_or_404(Group, name='top-management')
        return group_admin in self.groups.all()
    
    def is_direction(self):
        group_admin=get_object_or_404(Group, name='direction')
        return group_admin in self.groups.all()
    
    def is_stage(self):
        group_admin=get_object_or_404(Group, name='stage')
        return group_admin in self.groups.all()
    
    def is_scolarite(self):
        group_admin=get_object_or_404(Group, name='scolarite')
        return group_admin in self.groups.all()
    
    def is_surveillance(self):
        group_admin=get_object_or_404(Group, name='surveillance')
        return group_admin in self.groups.all()
    
    
    def is_enseignant(self):
        group_enseignant=get_object_or_404(Group, name='enseignant')
        return group_enseignant in self.groups.all()
    
    def is_etudiant(self):
        group_etudiant=get_object_or_404(Group, name='etudiant')
        return group_etudiant in self.groups.all()
    
    def is_personnel(self):
        group_personnel=get_object_or_404(Group, name='personnel')
        return group_personnel in self.groups.all()

    def is_regisseur(self):
        group_regisseur=get_object_or_404(Group, name='regisseur')
        return group_regisseur in self.groups.all()
    
    def is_not_etudiant(self):
        return not self.is_etudiant()
    
    
    def is_coordinateur(self, module_):
        if self.is_enseignant():
            return self.enseignant == module_.coordinateur
        else:
            return self.is_direction()
    
    def is_tuteur(self, etudiant_pk):
        if self.is_enseignant():
            etudiant_=get_object_or_404(Etudiant, matricule=etudiant_pk)
            if etudiant_.tuteur == self.enseignant:
                return True
            else:
                return False
        else:
            return self.is_direction()
    
    def is_staff_only(self):
        return self.is_direction() or self.is_scolarite() or self.is_surveillance() or self.is_stage() or self.is_top_management()
         
    def is_staff_or_student_himself(self, etudiant_pk):
        if self.is_staff_only() or self.is_enseignant():
            return True
        elif self.is_etudiant():
            return (self.etudiant.matricule == etudiant_pk) 
        else :
            return False
    
    def is_staff_or_teacher_himself(self, enseignant_pk):
        if self.is_staff_only():
            return True
        elif self.is_enseignant():
            return self.enseignant.id == enseignant_pk
        else :
            return False

class Institution(models.Model):
    nom = models.CharField(max_length=100)
    nom_a = models.CharField(max_length=100, default='')
    sigle = models.CharField(max_length=10)
    adresse = models.TextField()
    ville = models.CharField(max_length=50, default='')
    ville_a = models.CharField(max_length=50, default='')
    tel = models.CharField(max_length=20, null=True, blank=True, validators=[RegexValidator('^[0-9\+]*$',
                               'Que des chiffres sans espaces et le + pour l\'international')])
    fax = models.CharField(max_length=20, null=True, blank=True, validators=[RegexValidator('^[0-9\+]*$',
                               'Que des chiffres sans espaces et le + pour l\'international')])
    web = models.URLField(null=True, blank=True)
    illustration_cursus = models.ImageField(upload_to='admin', null=True, blank=True )
    logo = models.ImageField(upload_to='admin', null=True, blank=True )
    logo_bis = models.ImageField(upload_to='admin', null=True, blank=True )
    banniere = models.ImageField(upload_to='admin', null=True, blank=True )
    header =  models.ImageField(upload_to='admin', null=True, blank=True )
    footer =  models.ImageField(upload_to='admin', null=True, blank=True )


class DomaineConnaissance(models.Model):
    '''
    Cette classe sert à catégoriser les matière en domaines de connaissance globaux
    '''
    intitule=models.CharField(max_length=80)
    def __str__(self):
        return str(self.intitule)


# Create your models here.

class Matiere(models.Model):
    '''
    La marière est l'élément de base de la formation.
    Une matière fait partie d'une Unité d'enseignement
    '''
    code=models.CharField(max_length=10)
    precision = models.CharField(max_length=5, null=True, blank=True)
    ddc=models.ForeignKey(DomaineConnaissance, on_delete=models.SET_NULL, null=True, blank=True)
    titre=models.CharField(max_length=80)
    titre_a=models.CharField(max_length=80, null=True, blank=True)
    titre_en=models.CharField(max_length=80, null=True, blank=True)
    coef=models.IntegerField(null=True)
    credit=models.IntegerField(null=True)
    edition=models.CharField(max_length=5, null=True, blank=True, default='2012')
    vh_cours=models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    vh_td=models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    pre_requis=models.TextField(null=True, blank=True)
    objectifs=models.TextField(null=True, blank=True)
    contenu=models.TextField(null=True, blank=True)
    travail_perso=models.TextField(null=True, blank=True)
    bibliographie=models.TextField(null=True, blank=True)
    mode_projet=models.BooleanField(default=False)
    pfe=models.BooleanField(default=False)
    
    def __str__(self):
        if self.precision:
            return self.code +' '+self.precision
        else:
            return self.code 




    
class Specialite(models.Model):
    code=models.CharField(max_length=5, primary_key=True)
    intitule=models.CharField(max_length=100)
    intitule_a=models.CharField(max_length=100, null=True, blank=True)
    title=models.CharField(max_length=100, null=True, blank=True)
    def __str__(self):
        return self.code

class AnneeUniv(models.Model):
    '''
    Année Universitaire qui comprend plusieurs formations
    '''
    annee_univ=models.CharField(max_length=9, unique=True, primary_key=True)
    debut=models.DateField()
    fin=models.DateField()
    encours=models.BooleanField(default=False,  blank=True)
    
    def annee_suivante(self):
        annee_univ_suivante_=int(self.annee_univ)+1
        annee_univ_suivante_pk=str(annee_univ_suivante_)
        annee_univ_, created=AnneeUniv.objects.get_or_create(annee_univ=annee_univ_suivante_pk, defaults={
                'annee_univ':annee_univ_suivante_pk,
                'debut': self.debut+datetime.timedelta(days=365),
                'fin': self.fin+datetime.timedelta(days=365),
                'encours':False
            })
        return annee_univ_

    def annee_precedente(self):
        annee_univ_precedente_=int(self.annee_univ)-1
        annee_univ_precedente_pk=str(annee_univ_precedente_)
        annee_univ_, created=AnneeUniv.objects.get_or_create(annee_univ=annee_univ_precedente_pk, defaults={
                'annee_univ':annee_univ_precedente_pk,
                'debut': self.debut+datetime.timedelta(days=-365),
                'fin': self.fin+datetime.timedelta(days=-365),
                'encours':False
            })
        return annee_univ_
    
    def __str__(self):
        return self.annee_univ

    

class Periode(models.Model):
    '''
    Ca peut être un semestre ou trimestre ou autre. 
    '''
    code=models.CharField(max_length=2, null=True, choices=(('S1','Semestre 1'),('S2', 'Semestre 2'), ('T1', 'Trimestre 1'),('T2', 'Trimestre 2'),('T3', 'Trimestre 3')))
    ordre=models.IntegerField()
    nb_semaines=models.IntegerField(null=True, blank=True, default=15)
    session=models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return self.code

SEXE=(
    ('M','Masculin'),
    ('F','Féminin'),
)

class Personnel(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    nom=models.CharField(max_length=50)
    eps=models.CharField(max_length=50, null=True, blank=True)
    prenom=models.CharField(max_length=50)
    nom_a=models.CharField(max_length=50, null=True, blank=True)
    eps_a=models.CharField(max_length=50, null=True, blank=True)
    prenom_a=models.CharField(max_length=50, null=True, blank=True)
    sexe=models.CharField(max_length=1, choices=SEXE, null=True, blank=True)
    tel=models.CharField(max_length=15, null=True, blank=True)
    bureau=models.CharField(max_length=10, null=True, blank=True)
    
    def __str__(self):
        return self.nom + ' ' + self.prenom

STATUT=(
    ('P','Permanent'),
    ('V','Vacataire'),
    ('A','Associé'),
)

GRADE=(
    ('MA.B','Maître Assistant B'),
    ('MA.A','Maître Assistant A'),
    ('MC.B','Maître de Conférences B'),
    ('MC.A','Maître de Conférences A'),
    ('PR','Professeur'),
)

SITUATION=(
    ('A','En activité'),
    ('D','Mise en disponibilité'),
    ('T','Détachement'),
    ('M','Congé de Maladie'),
    ('I','Invalidité'),
    ('R','Retraité'),
    ('X','Départ: Mutation, Démission, ...'),
)

class Enseignant(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    nom=models.CharField(max_length=50)
    eps=models.CharField(max_length=50, null=True, blank=True)
    prenom=models.CharField(max_length=50)
    nom_a=models.CharField(max_length=50, null=True, blank=True)
    eps_a=models.CharField(max_length=50, null=True, blank=True)
    prenom_a=models.CharField(max_length=50, null=True, blank=True)
    sexe=models.CharField(max_length=1, choices=SEXE, null=True, blank=True)
    tel=models.CharField(max_length=15, null=True, blank=True)
    grade=models.CharField(max_length=4, choices=GRADE, null=True, blank=True)
    charge_statut=models.DecimalField(max_digits=5, decimal_places=2, default=288)
    situation=models.CharField(max_length=1, null=True, blank=True, choices=SITUATION, default='A')
    statut=models.CharField(max_length=1, null=True, blank=True, choices = STATUT, default='P')
    bureau=models.CharField(max_length=10, null=True, blank=True)
    bal=models.PositiveSmallIntegerField(null=True, blank=True)
    edt=models.TextField(null=True,blank=True)
    webpage=models.URLField(null=True, blank=True)
    otp=models.CharField(max_length=6, null=True, blank=True, default='')
    
    def set_otp(self):
        self.otp=str(randint(100000,999999))
        self.save(update_fields=['otp'])
        return self.otp
    
    def get_otp(self):
        return self.otp
    
    @transaction.atomic
    def check_otp(self, value):
        if self.otp=='':
            return False
        else:
            validity=(value==self.otp)
            self.otp=''
            return validity
    
    def ratio_charge_annuelle_encours(self):
        charge_list = Charge.objects.filter(realisee_par=self, annee_univ__encours=True)
        somme=0
        for charge_ in charge_list:
            if charge_.repeter_chaque_semaine:
                somme+=charge_.vh_eq_td * 15
            else:
                somme+=charge_.vh_eq_td
        return round(100,2) if self.statut=='V' else round(somme/self.charge_statut*100,2)
    
    def nb_avis(self):
        return Validation.objects.filter(pfe__groupe__isnull=True, expert=self.id).count()
    
    def nb_avis_vides(self):
        return Validation.objects.filter(pfe__groupe__isnull=True, expert=self.id, avis='X').count()
    
    def nb_encadrements(self):
        return PFE.objects.filter(groupe__section__formation__annee_univ__encours=True, coencadrants__in=[self]).count()
    def __str__(self):
        return str(self.nom)+' '+str(self.prenom)
        
class Departement(models.Model):
    intitule=models.CharField(max_length=100)
    intitule_a=models.CharField(max_length=100, null=True, blank=True)
    responsable=models.ForeignKey(Enseignant, on_delete=models.SET_NULL, null=True, blank=True)
    reglement=models.FileField(upload_to='admin', null=True, blank=True)
    signature=models.ImageField(upload_to='admin', null=True, blank=True)
    cycle_intitule=models.CharField(max_length=100, null=True, blank=True)
    cycle_ordre=models.PositiveSmallIntegerField(null=True, blank=True)
    
    def __str__(self):
        return self.intitule

class Diplome(models.Model):
    intitule=models.CharField(max_length=100)
    intitule_a=models.CharField(max_length=100, null=True)
    domaine = models.CharField(max_length=100, null=True)
    filiere = models.CharField(max_length=100, null=True)
    def __str__(self):
        return self.intitule
    
class Programme(models.Model):
    '''
    description statique des programmes
    '''
    code=models.CharField(max_length=8, unique=True)
    titre=models.CharField(max_length=100)
    titre_a=models.CharField(max_length=100, null=True)
    specialite=models.ForeignKey(Specialite, null=True, blank=True, on_delete=models.SET_NULL)
    description=models.TextField()
    diplome=models.ForeignKey(Diplome, on_delete=models.SET_NULL, null=True, blank=True)
    departement=models.ForeignKey(Departement, on_delete=models.SET_NULL, null=True, blank=True)
    ordre=models.PositiveSmallIntegerField(null=True, blank=True)
    # si concours à la fin de ce programme car ça influt sur les décisions de jurys possibles.
    concours=models.BooleanField(default=False)
    assistant=models.ForeignKey(Personnel, on_delete=models.SET_NULL, null=True, blank=True)

    
    def aggregate_avg_decision_jury(self):
        formation_list=Formation.objects.filter(programme=self, annee_univ__encours=False)
        aggregate={
            'admis':0,
            'admis_rachat':0,
            'redouble':0,
            'non_admis':0,
            'abandon':0,
            'non_inscrit':0,
            'maladie':0,
            'success':0,
            'echec':0,
            'refaire':0,
            'total':0
            }
        nb_formation=0
        for formation_ in formation_list:
            aggregate_formation=formation_.aggregate_decision_jury()
            if aggregate_formation:
                nb_formation+=1
                for key in (aggregate.keys()):
                    if key=='total':
                        aggregate['total']+=aggregate_formation['total']
                    elif float(aggregate_formation['total'])!=0:
                        # on calcul le purcentage pour les autres aggrégats
                        aggregate[key]+=float(aggregate_formation[key])/float(aggregate_formation['total'])*100.00

        if nb_formation>0:
            # on calcule la moyenne
            for key in aggregate.keys():
                if key=='total':
                    aggregate[key]=int(round(aggregate[key]/nb_formation,0))
                else:
                    aggregate[key]=round(aggregate[key]/nb_formation,2)
            return aggregate
        else:
            return None

    def programme_suivant(self):
        programme_suivant_list=Programme.objects.filter(ordre=self.ordre+1)
        if programme_suivant_list.count()==1:
            return programme_suivant_list.get()
        else:
            programme_suivant_list=Programme.objects.filter(ordre=self.ordre+1, specialite=self.specialite)
            if programme_suivant_list.count()==1:
                return programme_suivant_list.get()
            else:
                return None
    
    def __str__(self):
        return self.code

PERIODES = (
    ('S1', 'Semestre 1'),
    ('S2', 'Semestre 2'),
    ('S3', 'Semestre 3'),
    ('S4', 'Semestre 4'),
    ('S5', 'Semestre 5'),
    ('S6', 'Semestre 6'),
    ('S5+S6', 'Semestre 5+6'),
)

class PeriodeProgramme(models.Model):
    periode=models.ForeignKey(Periode, on_delete=CASCADE)
    programme=models.ForeignKey(Programme, on_delete=CASCADE, related_name='periodes')
    # Ce code correspond à la codification du décrêt, par exemple en 2CS ce sera S3, S4, en 3CS, S5, S6
    # L'attribut code de la classe Periode correspond à la période chronologique dans l'année S1, S2, ou TR1, TR2, TR3, ...
    code = models.CharField(max_length = 10, null =True, blank=True, choices = PERIODES)
    
    def nb_matieres(self):
        somme=0
        for ue in self.ues.all():
            somme+=ue.nb_matieres()
        return somme

    def credit(self):
        somme=0
        ue_option_comptabilisee_list=[]
        for ue in self.ues.all():
            if ue.nature=='OBL':
                somme+=ue.credit()
            elif not ue.code in ue_option_comptabilisee_list:
                somme+=ue.credit()
                ue_option_comptabilisee_list.append(ue.code) 
        return somme
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['programme', 'periode'], name="periode-programme")
        ]

    def __str__(self):
        return str(self.programme)+ ' '+str(self.periode)

CAT_UE = (
    ('F','UE Fondamentale'),
    ('M','UE Méthodologique'),
    ('T','UE Transversale'),
    ('D','UE Découverte'),
)

class UE(models.Model):
    '''
    Un programme est composé de plusieurs UE
    '''
    '''
    Une UE obligatoire figure nécessairement dans tous les relevés de note
    Une UE optionnelle est composée de matières au choix dans la limite du nombre de crédits alloués à l'UE
    Donc plusieurs instances de l'UE sont créées en fonction des choix
    C'est dans Formation qui est l'instance temporelle de Programme qu'on fixe la liste des options retenues pour la promotion
    Puis dans le groupe on précise les UE spécifique à une option
    '''
    NATURES = (
        ('OBL','Obligatoire'),
        ('OPT','Optionnelle'),
    )
    code=models.CharField(max_length=8)
    type=models.CharField(max_length=1, choices=CAT_UE)
    nature=models.CharField(max_length=3, choices=NATURES, null=True)
    matieres=models.ManyToManyField(Matiere, blank=True, related_name='matiere_ues')
    periode=models.ForeignKey(PeriodeProgramme, on_delete=CASCADE, null=True, blank=True, related_name='ues')
    coefold=models.IntegerField(null=True)
    
    def nb_matieres(self):
        return self.matieres.all().count()
    
    def coef(self):
        somme=0
        for matiere in self.matieres.all():
            somme+=matiere.coef
        return somme
    
    def credit(self):
        somme=0
        for matiere in self.matieres.all():
            somme+=matiere.credit
        return somme

    def __str__(self):
        list_matieres=''
        for matiere in self.matieres.all():
            list_matieres+=' '+matiere.code
        return self.code+ ' ' +str(self.periode)+list_matieres

# DECISIONS_JURY=(
#     ('C','En cours'),
#     ('A','Admis'),
#     ('AR','Admis avec Rachat'),
#     ('R','Redouble'),
#     ('F','Abandon'),
#     ('M','Maladie'),
#     ('N','Non Admis'),
#     ('X','Non Inscrit'),
# )

 
class Formation(models.Model):
    '''
    Formation correspond à un pallier ou spécialité
    '''
    programme=models.ForeignKey(Programme, on_delete=CASCADE)
    annee_univ=models.ForeignKey(AnneeUniv, on_delete=CASCADE)
    archive=models.BooleanField(default=False)
    
    def pv_existe(self, periode_):
        if PV.objects.filter(formation=self.id, annuel=True):
            return True
        else:
            return PV.objects.filter(formation=self.id, periode=periode_).count() > 0
        
    def inscriptions_actives(self):
        return Inscription.objects.filter(formation=self).exclude(Q(inscription_periodes__groupe__isnull=True)|Q(decision_jury='X')|Q(decision_jury__startswith='F')|Q(decision_jury__startswith='M'))

    def inscriptions_pour_deliberations(self):
        return Inscription.objects.filter(formation=self).exclude(Q(inscription_periodes__groupe__isnull=True)|Q(decision_jury='X'))

    def inscriptions_encours(self):
        return Inscription.objects.filter(formation=self, decision_jury='C')
    
    def pre_inscriptions(self):
        return Inscription.objects.filter(formation=self, decision_jury='X')
    
    def aggregate_decision_jury(self):
        inscription_list=Inscription.objects.filter(formation=self)
        admis_count=Count('decision_jury', filter=Q(decision_jury='A')|Q(decision_jury='AC'))
        admis_rachat_count=Count('decision_jury', filter=Q(decision_jury='AR')|Q(decision_jury='CR'))
        encours_count=Count('decision_jury', filter=Q(decision_jury='C'))
        non_admis_count=Count('decision_jury', filter=Q(decision_jury='N'))
        redouble_count=Count('decision_jury', filter=Q(decision_jury='R'))
        abandon_count=Count('decision_jury', filter=Q(decision_jury__startswith='F'))
        maladie_count=Count('decision_jury', filter=Q(decision_jury__startswith='M'))
        non_inscrit_count=Count('decision_jury', filter=Q(decision_jury='X')|Q(groupe__isnull=True))
        total_count=Count('decision_jury', filter=Q(decision_jury='A') |Q(decision_jury='AC') | Q(decision_jury='AR') | Q(decision_jury='CR') | Q(decision_jury='C')| Q(decision_jury__startswith='F')| Q(decision_jury__startswith='M')| Q(decision_jury='R')| Q(decision_jury='N'))
        if inscription_list.exists():
            aggregate_data=inscription_list.values('formation').annotate(
                admis=admis_count).annotate(
                admis_rachat=admis_rachat_count).annotate(    
                encours=encours_count).annotate(
                non_admis=non_admis_count).annotate(
                redouble=redouble_count).annotate(
                abandon=abandon_count).annotate(
                maladie=maladie_count).annotate(
                non_inscrit=non_inscrit_count).annotate(
                total=total_count).annotate(
                success=admis_count+admis_rachat_count).annotate(
                echec=abandon_count+non_admis_count).annotate(
                refaire=redouble_count+maladie_count)
        else:
            return None
        return aggregate_data[0]
    
    def formation_sup_annee_suivante(self):
        #annee_courante=AnneeUniv.objects.get(annee_univ=self.annee_univ)
        annee_suivante_=self.annee_univ.annee_suivante()
        #programme_courant=Programme.objects.get(id=self.programme)
        programme_suivant_=self.programme.programme_suivant()
        if programme_suivant_:
            formation_sup_annee_suivante_, created=Formation.objects.get_or_create(annee_univ=annee_suivante_, programme=programme_suivant_, defaults={
                    'annee_univ':annee_suivante_,
                    'programme':programme_suivant_,
                    'archive':False
                })
            return formation_sup_annee_suivante_
        else:
            return None

    def formation_idem_annee_suivante(self):
        #annee_courante=AnneeUniv.objects.get(annee_univ=self.annee_univ)
        annee_suivante_=self.annee_univ.annee_suivante()
        formation_idem_annee_suivante_, created=Formation.objects.get_or_create(annee_univ=annee_suivante_, programme=self.programme, defaults={
                'annee_univ':annee_suivante_,
                'programme':self.programme,
                'archive':False
            })
        return formation_idem_annee_suivante_
         
    def __str__(self):
        return str(self.programme) + ' ' +str(self.annee_univ)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['programme', 'annee_univ'], name="programme-annee_univ")
        ]

class PeriodeFormation(models.Model):
    formation = models.ForeignKey(Formation, on_delete=CASCADE, null=True, blank=True, related_name='periodes')
    periode = models.ForeignKey(Periode, on_delete=CASCADE, null=True, blank=True)
    session = models.CharField(max_length=20, null=True, blank=True)
    
    def __str__(self):
        return str(self.formation)+' '+self.periode.code +' '+self.session
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['formation', 'periode'], name="formation-periode")
        ]

class PV(models.Model):
    formation=models.ForeignKey(Formation, on_delete=models.SET_NULL, null=True, blank=True)
    content=models.TextField()
    annuel=models.BooleanField(default=False)
    periode=models.ForeignKey(Periode, on_delete=models.SET_NULL, null=True, blank=True)
    tri_rang=models.BooleanField(default=True)
    photo=models.BooleanField(default=True)
    anonyme=models.BooleanField(default=False)
    note_eliminatoire=models.BooleanField(default=True)
    moy_ue=models.BooleanField(default=False)
    rang=models.BooleanField(default=True)
    signature=models.BooleanField(default=True)
    reserve=models.BooleanField(default=False)
    date=models.DateField(null=True, blank=True)

    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['formation', 'annuel', 'periode', 'tri_rang', 'photo', 'anonyme', 'note_eliminatoire', 'rang','signature'], name="pv_config")
        ]
    def __str__(self):
        pv='PV '+str(self.formation)
        if not self.annuel:
            pv+=' '+str(self.periode)
        elif self.tri_rang:
            pv+=' Rang'
        elif self.note_eliminatiore:
            pv+=' NE'
        elif self.photo:
            pv+=' Photos'
        elif self.signature:
            pv+=' Sig'
        return pv
    

class Module(models.Model):
    '''
    Il s'agit d'une instance d'une matière dans une formation
    '''
    matiere=models.ForeignKey(Matiere, on_delete=CASCADE)
    formation=models.ForeignKey(Formation, on_delete=CASCADE, related_name='modules')
    periode=models.ForeignKey(PeriodeProgramme, on_delete=models.SET_NULL, null=True, blank=True)
    # TODO on doit pas cascader delete de periode sinon on perd la base en un click
    coordinateur=models.ForeignKey(Enseignant, on_delete=models.SET_NULL, null=True, blank=True)
    note_eliminatoire=models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, default=5.0)
    
    def pv_existe(self):
        return self.formation.pv_existe(self.periode.periode)
    
    def calcul_note_eliminatoire(self):
        # on considère les résultats de tous les étudiants qui suivent la formation
        # on exclut du calcul les malades et abandons
        resultat_list=Resultat.objects.filter(inscription__formation=self.formation, module=self).exclude(inscription__decision_jury__startswith='M').exclude(inscription__decision_jury__startswith='F').exclude(inscription__decision_jury='X').exclude(inscription__groupe__isnull=True)
        if resultat_list.exists():
            resultat_avg=resultat_list.values('module').annotate(moyenne=Avg('moy')).get()
            note_eliminatoire=round(resultat_avg['moyenne']*decimal.Decimal(0.60),2)
        else:
            note_eliminatoire=round(decimal.Decimal(5.0),2)
        if note_eliminatoire>=decimal.Decimal(10.0):
            note_eliminatoire=round(decimal.Decimal(9.99),2)
        elif note_eliminatoire<decimal.Decimal(5.0):
            note_eliminatoire=round(decimal.Decimal(5.0),2)
            
        return note_eliminatoire

    def nb_absences(self, etudiant_):
        nb = AbsenceEtudiant.objects.filter(etudiant=etudiant_, seance__activite__module=self).count()
        return nb
    
    def nb_etudiants_avec_ne(self):
        return Resultat.objects.filter(inscription__formation=self.formation, module=self, moy__lt=self.note_eliminatoire).exclude(inscription__decision_jury__startswith='M').exclude(inscription__decision_jury__startswith='F').exclude(inscription__decision_jury='X').exclude(inscription__groupe__isnull=True).count()

    def nb_etudiants_avec_ne_calculee(self):
        return Resultat.objects.filter(inscription__formation=self.formation, module=self, moy__lt=self.calcul_note_eliminatoire()).exclude(inscription__decision_jury__startswith='M').exclude(inscription__decision_jury__startswith='F').exclude(inscription__decision_jury='X').exclude(inscription__groupe__isnull=True).count()

    def moy(self):
        aggregate=Resultat.objects.filter(inscription__formation=self.formation, module=self
                                        ).exclude(inscription__decision_jury__startswith='M'
                                        ).exclude(inscription__decision_jury__startswith='F'
                                        ).exclude(inscription__decision_jury='X'
                                        ).aggregate(moy=Avg('moy'))
        return round(aggregate['moy'],2)
    
    def somme_ponderation(self):
        if self.evaluations.filter(ponderation__isnull=False).exists():
            aggregate=self.evaluations.all().aggregate(somme=Sum('ponderation'))
            return round(aggregate['somme'],2)
        else:
            return 0
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['matiere', 'formation', 'periode'], name="matiere-formation")
        ]
        indexes = [
            models.Index(fields=['formation', 'periode'])
        ]
        
    def __str__(self):
        return str(self.formation)+' '+str(self.matiere)+ ' '+str(self.periode)
    
class Evaluation(models.Model):
    '''
    On définit ici les évlautaions prévues dans un module
    '''
    TYPES_EVAL=(
        ('CF','Contrôle Final'),
        ('CI','Contrôle Intérmédiaire'),
        ('INT','Interrogation'),
        ('TP','Travail Pratique'),
        ('CC','Contrôle Continu'),
        ('Rapporteur','PFE: Evaluation du rapport'),
        ('Jury','PFE: Evaluation du jury'),
        ('Encadreur','PFE: Evaluation de l\'encadreur'),
        ('Rapport','Master: Evaluation du rapport'),
        ('Soutenance','Master: Evaluation de l\'oral'),
        ('Poster','Master: Evaluation du Poster'),
        
    )
    type=models.CharField(max_length=15,choices=TYPES_EVAL)
    ponderation=models.DecimalField(max_digits=3, decimal_places=2, default=0)
    module=models.ForeignKey(Module,on_delete=CASCADE, related_name='evaluations')

    def __str__(self):
        return self.type + ' ' + str(self.module)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['type', 'module'], name="eval-module")
    ]

    
class Section(models.Model):
    '''
    Section de cours. Une formation est organisée en sections
    '''
    CODES_SEC=(
        ('A','Section A'),
        ('B','Section B'),
        ('C','Section C'),
        ('D','Section D'),
        ('E','Section E'),
    )
    code=models.CharField(max_length=1,null=True,choices=CODES_SEC)
    formation=models.ForeignKey(Formation, on_delete=CASCADE, null=True, related_name='sections')

    def taille(self):
        somme=0
        for groupe_ in self.groupes.all().exclude(code__isnull=True):
            somme+=groupe_.inscrits.all().count()
        return somme

    def __str__(self):
        return self.formation.programme.code + ' Section '+self.code

CODES_GRP=(

    ('G01','Groupe 01'),
    ('G02','Groupe 02'),
    ('G03','Groupe 03'),
    ('G04','Groupe 04'),
    ('G05','Groupe 05'),
    ('G06','Groupe 06'),
    ('G07','Groupe 07'),
    ('G08','Groupe 08'),
    ('G09','Groupe 09'),
    ('G10','Groupe 10'),
    ('G11','Groupe 11'),
    ('G12','Groupe 12'),
)
    

class Groupe(models.Model):
    '''
    Groupe de TD ou TP
    UN groupe appartient à une section
    Un groupe particulier est créé automatiquement pour représenter une section et qui porte un code null
    '''
    code=models.CharField(max_length=10,null=True,blank=True)
    section=models.ForeignKey(Section, on_delete=CASCADE, null=True, related_name='groupes')
    option=models.ManyToManyField(UE, blank=True)
    edt=models.TextField(null=True,blank=True, default='Agenda Empty')

    def gCal(self):
        # L'agenda correspondant à un groupe doit porter comme nom/code:
        # code programme (1CP, 2SL, ....) section (A, B, C, ...) et code groupe si c'est un groupe (G01, G02, ...)
        gCalCode = self.section.formation.programme.code+' '+self.section.code
        if self.code:
            gCalCode+=' '+self.code
        try:
            gCal_=GoogleCalendar.objects.get(code=gCalCode)
        except Exception:
            return None
        return gCal_
     
    def taille(self):
        if self.code:
            aggregate=InscriptionPeriode.objects.filter(groupe=self).exclude(Q(inscription__decision_jury__startswith='F')|Q(inscription__decision_jury__startswith='M')).values('periodepgm__periode__code').annotate(taille=Count('inscription')).order_by('periodepgm__periode__code')
            #return self.inscrits.all().count()
            return aggregate
        else:
            aggregate=InscriptionPeriode.objects.filter(groupe__section=self.section).exclude(Q(inscription__decision_jury__startswith='F')|Q(inscription__decision_jury__startswith='M')).values('periodepgm__periode__code').annotate(taille=Count('inscription')).order_by('periodepgm__periode__code')
#             somme={}
#             for groupe_ in self.section.groupes.all().exclude(code__isnull=True):
#                 somme+=groupe_.inscrits.all().count()
#             return somme
            return aggregate
        
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['code', 'section'], name="groupe-section")
        ]

    def __str__(self):
        if self.code:
            return str(self.section.formation.programme.code)+' '+ str(self.code)
        else:
            return str(self.section)

class ModulesSuivis(models.Model):
    SAISIE_ETAT=(
        ('N','Pas encore'),
        ('C','En cours'),
        ('T','Terminé'),
    )

    module=models.ForeignKey(Module, on_delete=CASCADE, related_name='groupes_suivis')
    groupe=models.ForeignKey(Groupe, on_delete=CASCADE, related_name='modules_suivis')
    saisie_notes=models.CharField(max_length=1, choices= SAISIE_ETAT, default='N')
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['module', 'groupe'], name="module-groupe")
        ]
        indexes = [
            models.Index(fields = ['module', 'groupe'])
        ]
        
    def __str__(self):
        return str(self.module)+' '+str(self.groupe)

TYPES_ACT=(
    ('C','Cours'),
    ('TD','Travail Dirigé'),
    ('TP','Travail Pratique'),
    ('P','Projet'),
    ('E_CI','Contrôle Intermédiaire'),
    ('E_CF','Contrôle Final'),
    ('E_CR','Contrôle de Remplacement'),
    ('E_In','Interrogation'),
    ('E_TP','Test TP'),
    ('PFE_Enc', 'Encadrement PFE'),
    ('PFE_Sout','Soutenance PFE'),
    ('Mem_Enc', 'Encadrement Master'),
    ('Mem_Sout','Soutenance Master'),

)

TYPES_ACT_EXAM=(
    ('E_CI','Contrôle Intermédiaire'),
    ('E_CF','Contrôle Final'),
    ('E_CR','Contrôle de Remplacement'),
    ('E_In','Interrogation'),
    ('E_TP','Test TP'),
)

class Activite(models.Model):
    '''
    Il y a plusieurs activités dans un module comme un cours + TD + TP ...
    '''
    type=models.CharField(max_length=10,choices=TYPES_ACT)
    module=models.ForeignKey(Module, on_delete=CASCADE)
    cible=models.ManyToManyField(Groupe, blank=True, related_name='activites')
    assuree_par=models.ManyToManyField(Enseignant, related_name='enseignants')
    vh=models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    repeter_chaque_semaine=models.BooleanField(default=True)
    repartir_entre_intervenants=models.BooleanField(default=False)
    
    def nb_etudiants(self):
        somme=0
        for groupe_ in self.cible.all():
            somme = somme + Inscription.objects.filter(groupe=groupe_).exclude(Q(decision_jury__startswith='F')|Q(decision_jury__startswith='M')|Q(decision_jury__startswith='X')).count()
        return somme
    
    def vh_par_enseignant(self):
        # calcul du volume horaire
        nb_intervenants=self.assuree_par.count()
        if nb_intervenants>0:
            if self.repartir_entre_intervenants:
                vh_=self.vh/nb_intervenants
            else:
                vh_=self.vh
        else:
            vh_=0.0
        return round(vh_,2)
    
    def vh_eq_td_par_enseignant(self):
        # calcul du volume horaire
        vh_=self.vh_par_enseignant()
        if self.type=='C':
            vh_=vh_*decimal.Decimal(1.5)
        return round(vh_,2)
            
        
    class Meta:
        indexes = [
            models.Index(fields=['module'])
        ]
    
    def __str__(self):
        cible_str=''
        for groupe_ in self.cible.all():
            cible_str+=' + '+str(groupe_)
        return dict(TYPES_ACT)[self.type] + ': ' +str(self.module.matiere.code)+' '+cible_str

TYPE_CHARGE=(
    ('E','Enseignement'),
    ('C','Encadrement'),
    ('J','Jury'),
    ('S','Surveillance'),
    ('A','Responsabilite Administrative'),
    ('M','Mission'),
    ('R','Réunion'),
)

class ActiviteChargeConfig(models.Model):
    categorie=models.CharField(max_length=5, choices=TYPE_CHARGE, null=True )
    type=models.CharField(max_length=10)
    titre=models.CharField(max_length=50, null=True)
    vh=models.DecimalField(max_digits=5, decimal_places=2, default=0)
    vh_eq_td=models.DecimalField(max_digits=5, decimal_places=2, default=0)
    repeter_chaque_semaine=models.BooleanField(default=True)
    repartir_entre_intervenants=models.BooleanField(default=False)
    def __str__(self):
        return dict(TYPE_CHARGE)[self.categorie]+' '+self.titre
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['type'], name="activite-charge_config")
        ]
    
class Charge(models.Model):
    '''
        Charge d'un enseignant issue de ses activités d'enseignement, encadrement, administration, surveillance, missions, etc.
    '''
    type=models.CharField(max_length=1, choices=TYPE_CHARGE)
    activite=models.ForeignKey(Activite, on_delete=CASCADE, null=True, blank=True)
    obs=models.CharField(max_length=50, null=True, blank=True)
    vh=models.DecimalField(max_digits=5, decimal_places=2, default=0)
    vh_eq_td=models.DecimalField(max_digits=5, decimal_places=2, default=0)
    annee_univ=models.ForeignKey(AnneeUniv, on_delete=models.SET_NULL, null=True)
    periode = models.ForeignKey(Periode, on_delete=models.SET_NULL, null=True)
    realisee_par=models.ForeignKey(Enseignant, on_delete=CASCADE, related_name='charges')
    cree_par=models.ForeignKey(Enseignant, on_delete=CASCADE, null=True, blank=True)
    repeter_chaque_semaine=models.BooleanField(default=False, null=True, blank=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['activite', 'realisee_par'], name="activite-enseignant")
        ]
        indexes = [
            models.Index(fields=['realisee_par'])
        ]

    def __str__(self):
        if self.activite:
            return str(self.type) + ' ' + str(self.activite) + ' ' + str(self.vh_eq_td)
        else:
            return str(self.type) + ' ' + str(self.obs) + ' ' + str(self.vh_eq_td)        

class Pays(models.Model):
    code=models.CharField(max_length=2, primary_key=True)
    nom=models.CharField(max_length=50)
    def __str__(self):
        return self.code+' '+self.nom

class Wilaya(models.Model):
    code=models.CharField(max_length=2, primary_key=True)
    nom=models.CharField(max_length=50)
    def __str__(self):
        return self.code+' '+self.nom

class Commune(models.Model):
    code_postal=models.CharField(max_length=5, primary_key=True)
    nom=models.CharField(max_length=50)
    wilaya=models.ForeignKey(Wilaya, on_delete=models.SET_NULL, null=True, related_name='communes')
    def __str__(self):
        return self.code_postal+' '+self.nom
    
    
   
class Etudiant(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    matricule=models.CharField(max_length=10,primary_key=True)
    nom=models.CharField(max_length=50)
    prenom=models.CharField(max_length=50)
    sexe=models.CharField(max_length=1, choices=SEXE, null=True, blank=True)
    date_naissance=models.DateField(null=True, blank=True)
    lieu_naissance=models.CharField(max_length=100, null=True, blank=True)
    wilaya_naissance=models.ForeignKey(Wilaya, on_delete=models.SET_NULL, null=True, blank=True)
    wilaya_residence=models.ForeignKey(Wilaya, on_delete=models.SET_NULL, null=True, blank=True, related_name='origines')
    commune_residence=models.ForeignKey(Commune, on_delete=models.SET_NULL, null=True, blank=True)
    interne=models.BooleanField(default=False, null=True, blank=True)
    residence_univ=models.TextField(null=True, blank=True)
    addresse_principale=models.TextField(null=True, blank=True)
    nom_a=models.CharField(max_length=50, null=True, blank=True)
    prenom_a=models.CharField(max_length=50, null=True, blank=True)
    lieu_naissance_a=models.CharField(max_length=100, null=True, blank=True)
    photo=models.ImageField(upload_to='photos',null=True,blank=True)
    activite_extra=models.TextField(null=True, blank=True)
    tuteur=models.ForeignKey(Enseignant, on_delete=models.SET_NULL, null=True, blank=True)    
    github=models.URLField(null=True, blank=True)
    linkdin=models.URLField(null=True, blank=True)
    public_profile=models.BooleanField(default=False)
    tel=models.CharField(max_length=15, null=True, blank=True)
    numero_securite_sociale=models.CharField(max_length=15, validators=[RegexValidator('^[0-9\+]*$',
                               'Que des chiffres sans espaces')], null=True, blank=True)
    
#     def rang_max(self):
#         aggregate=Etudiant.objects.filter(matricule=self.matricule).aggregate(rang_max=Max('inscriptions__rang'))
#         return aggregate['rang_max']
#     def annee_encours(self):
#         return self.inscriptions.all().get(formation__programme__encours=True).values('formation__programme')
    def inscriptions_encours(self):
        return Inscription.objects.filter(etudiant=self, formation__annee_univ__encours=True)
    
    def nb_depots_stages(self):
        return PFE.objects.filter(groupe__isnull=True, reserve_pour__etudiant__in=[self]).count()
    
    def eligible_pfe(self):
        eligible_=False
        for inscription_ in self.inscriptions_encours():
            if inscription_.formation.programme.ordre >= 4:
                eligible_=True
        return eligible_
    
    def __str__(self):
        return self.matricule+' '+ self.nom + ' ' + self.prenom

class Salle(models.Model):
    code= models.CharField(max_length=50)
    capacity= models.PositiveSmallIntegerField(default=0)
    calendarId= models.CharField(max_length=100, null=True, blank=True)
    nb_lignes= models.PositiveSmallIntegerField(default=0)
    nb_colonnes= models.PositiveSmallIntegerField(default=0)
    
    def capacite(self):
        return self.places.filter(disponible=True).count()
    
    def place_disponible_list(self):
        return self.places.filter(disponible=True).order_by('places__code')

    def __str__(self):
        return self.code
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['code'], name="salle-code")
        ]
    
class Place(models.Model):
    code = models.CharField(max_length=3)
    disponible = models.BooleanField(default=True)
    salle = models.ForeignKey(Salle, on_delete=CASCADE, related_name='places')
    num_ligne = models.PositiveSmallIntegerField(default=0)
    num_colonne = models.CharField(max_length=1)
    
    def __str__(self):
        return str(self.salle) +'('+self.code+')'
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['salle','code'], name="salle-place")
        ]
     
class Seance(models.Model):
    '''
    Instance d'une activité durant le semestre
    '''
    date=models.DateField()
    heure_debut=models.TimeField(null=True, blank=True)
    heure_fin=models.TimeField(null=True, blank=True)
    salles=models.ManyToManyField(Salle, blank=True)
    activite=models.ForeignKey(Activite, on_delete=CASCADE)
    rattrapage=models.BooleanField(default=False)

    def __str__(self):
        return dict(TYPES_ACT)[self.activite.type]+' ' +str(self.activite.module) + ' '+str(self.date)+ (' R' if self.rattrapage else '')

    def get_absolute_url(self):
        return reverse('seance_detail', kwargs={'seance_pk': self.pk})

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['activite', 'date', 'heure_debut', 'heure_fin'], name="seance")
        ]

class AbsenceEtudiant(models.Model):
    '''
    Permet de stocker les absences et leurs justifications
    '''
    etudiant=models.ForeignKey(Etudiant, on_delete=CASCADE, null=True, blank=True)
    seance=models.ForeignKey(Seance, on_delete=CASCADE, null=True, blank=True)
    justif=models.BooleanField(default=False)
    motif=models.TextField(max_length=50, null=True, blank=True)
    date_justif=models.DateField(null=True, blank=True)  
    
    def nb_absences(self):
        aggregate = AbsenceEtudiant.objects.filter(etudiant=self.etudiant, seance__activite__module=self.seance.activite.module).aggregate(nb_absences=Count('etudiant'))
        return aggregate['nb_absences']
    

    def __str__(self):
        return str(self.etudiant) +' '+str(self.seance)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['etudiant', 'seance'], name="etudiant-seance")
        ]

class AbsenceEnseignant(models.Model):
    '''
    Permet de stocker les absences et leurs justifications
    '''
    enseignant=models.ForeignKey(Enseignant, on_delete=models.CASCADE, null=True, blank=True)
    seance=models.ForeignKey(Seance, on_delete=CASCADE, null=True, blank=True)
    justif=models.BooleanField(default=False)
    date_justif=models.DateField(null=True, blank=True)
    motif=models.TextField(max_length=50, null=True, blank=True)
    seance_remplacement=models.ForeignKey(Seance, on_delete=CASCADE, null=True, blank=True, related_name='remplacement')

    def nb_absences(self):
        aggregate = AbsenceEnseignant.objects.filter(enseignant=self.enseignant, seance__activite__module=self.seance.activite.module).aggregate(nb_absences=Count('enseignant'))
        return aggregate['nb_absences']
    
    def __str__(self):
        return str(self.enseignant) +' '+str(self.seance)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['enseignant', 'seance'], name="enseignant-seance")
        ]
    
MENTION=(
    ('T','Très Bien'),
    ('B','Bien'),
    ('A','Assez Bien'),
    ('P','Passable'),
    ('F', 'Ajournement'),
    ('X', 'Non concerné')
)

DECISIONS_JURY=(
    ('C','Inscrit'),
    ('A','Admis'),
    ('AR','Admis avec Rachat'),
    ('AC','Admis au Concours'),
    ('CR','Admis au Concours avec Rachat'),
    ('R','Redouble'),
    ('AJ','Ajournement'),
    ('P','Prolongation'),
    ('F','Abandon'),
    ('FT','Transfert'),
    ('M', 'Maladie'),
    ('M1', 'Congé académique (année blanche) pour raisons médicales'),
    ('M2', 'Congé académique (année blanche) pour raisons personnelles'),
    ('M3', 'Congé académique (année blanche) pour raisons personnelles (Covid 19)'),
    ('M4', 'Congé académique (année blanche) pour raisons familiales'),
    ('N','Non Admis'),
    ('X','Non Inscrit'),
)

OPTIONS_DEPOT=(
    (1,'Oui'),
    (2,'Oui avec des corrections à faire'),
    (3,'Non'),
)

class Soutenance(models.Model):
    groupe = models.OneToOneField(Groupe, on_delete=CASCADE, null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    depot_biblio = models.SmallIntegerField(default=3, choices=OPTIONS_DEPOT)
    president = models.ForeignKey(Enseignant, on_delete=models.SET_NULL, null=True, blank=True, related_name='president')
    rapporteur = models.ForeignKey(Enseignant, on_delete=models.SET_NULL, null=True, blank=True, related_name='rapporteur')
    examinateur = models.ForeignKey(Enseignant, on_delete=models.SET_NULL, null=True, blank=True, related_name='examinateur')
    coencadrant = models.ForeignKey(Enseignant, on_delete=models.SET_NULL, null=True, blank=True, related_name='coencadrant')
    assesseur1 = models.ForeignKey(Enseignant, on_delete=models.SET_NULL, null=True, blank=True, related_name='assesseur1')
    assesseur2 = models.ForeignKey(Enseignant, on_delete=models.SET_NULL, null=True, blank=True, related_name='assesseur2')
    invite1 = models.CharField(max_length=100, null=True, blank=True)
    invite2 = models.CharField(max_length=100, null=True, blank=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['groupe'], name="groupe-soutenance")
        ]
    
    def __str__(self):
        return str(self.groupe)+' : '+str(self.date)
    
class Inscription(models.Model):
    etudiant=models.ForeignKey(Etudiant, on_delete=CASCADE, related_name='inscriptions')
    formation=models.ForeignKey(Formation,on_delete=CASCADE)
    groupe=models.ForeignKey(Groupe, null=True, blank=True, on_delete=models.SET_NULL, related_name='inscrits')
    moy=models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, default=0)
    #moy_post_delib=models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, default=0)
    rang=models.PositiveSmallIntegerField(null=True, blank=True, default=0)
    decision_jury=models.CharField(max_length=2,choices=DECISIONS_JURY, null=True, blank=True, default='X')
    # proposition decision_jury qui ne soit pas vue par les étudiants, avant confirmation déliberations
    proposition_decision_jury=models.CharField(max_length=2,choices=DECISIONS_JURY, null=True, blank=True, default='X')
    obs_jury=models.CharField(max_length=50, null=True, blank=True)
    mention = models.CharField(max_length=2, choices=MENTION, null=True, blank=True, default='X')
    quittance = models.ImageField(upload_to='quittances', null=True, blank=True )
    
    def credits_obtenus(self):
        somme=0
        if self.moy_post_delib() >= 10:
            for periode in self.inscription_periodes.all():
                for resultat_ue in periode.resultat_ues.all():
                    for resultat in resultat_ue.resultat_matieres.all():
                        if resultat.moy_post_delib >=resultat.module.note_eliminatoire:
                            somme+=resultat.module.matiere.credit
        else:
            for periode in self.inscription_periodes.all():
                somme+=periode.credits_obtenus()
        return somme
    
    def credits_cursus(self):
        somme=self.credits_obtenus()
        for inscription in Inscription.objects.filter(Q(etudiant=self.etudiant)& 
                                                      Q(formation__programme__ordre__lt=self.formation.programme.ordre)&
                                                      (Q(decision_jury='A')|Q(decision_jury='AR'))):
            somme+=inscription.credits_obtenus()
        return somme
    
    def ects_credits(self):
        #cette méthode est obsolète, utiliser credits_obtenus conforme à la réglementation en vigueur
        somme=0
        for periode in self.inscription_periodes.all():
            somme+=periode.ects_credits()
        return somme

    def ects_cursus(self):
        #cette méthode est obsolète, utiliser credits_cursus conforme à la réglementation en vigueur
        somme=self.ects_credits()
        for inscription in Inscription.objects.filter(Q(etudiant=self.etudiant)& 
                                                      Q(formation__programme__ordre__lt=self.formation.programme.ordre)&
                                                      (Q(decision_jury='A')|Q(decision_jury='AR'))):
            somme+=inscription.ects_credits()
        return somme
    
    def nb_inscrits(self):
        return self.formation.inscriptions_pour_deliberations().count()
    
    def nb_ne(self):
        nb_ne=0
        for periode in self.inscription_periodes.all():
            nb_ne+=periode.nb_ne()
        return nb_ne
        
    
    def moyenne(self):
        moy=0
        coef_sum=0
        for inscription_periode in self.inscription_periodes.all():
            moy += inscription_periode.moyenne()
            coef_sum += 1
        if coef_sum>0:
            return round(moy / coef_sum,2)
        else:
            return 0
    
    def moyenne_post_delib(self):
        moy=0
        coef_sum=0
        for inscription_periode in self.inscription_periodes.all():
            moy += inscription_periode.moy_post_delib()
            coef_sum += 1
        if coef_sum>0:
            return round(moy / coef_sum,2)
        else:
            return 0
    
    def moy_post_delib(self):
        # Cette méthode est similaire à la précédente et a été introduite pour garder le code qui se base sur 
        # l'attribut moy_post_delib supprimé
        return self.moyenne_post_delib()
    
    def ranking(self):
        aggregate = Inscription.objects.filter(formation=self.formation, moy__gt=self.moy).exclude(Q(groupe__isnull=True)|Q(decision_jury='X')).aggregate(ranking=Count('moy'))
        return aggregate['ranking'] + 1

    def moy_globale(self):
        aggregate = Inscription.objects.filter(
                Q(etudiant=self.etudiant) & 
                Q(formation__programme__diplome=self.formation.programme.diplome) &
                Q(formation__programme__ordre__lte=self.formation.programme.ordre) &
                (Q(decision_jury='A')|Q(decision_jury='AR'))
            ).aggregate(moy_generale=Avg('moy'))
        if aggregate['moy_generale']:
            return round(aggregate['moy_generale'],2)
        else:
            return 0.0
    
    def ranking_global(self):
        list_inscrits = self.formation.inscriptions_pour_deliberations()
        list_moyennes_globales=[]
        for inscrit in list_inscrits:
            list_moyennes_globales.append(inscrit.moy_globale())
        list_moyennes_globales.sort(reverse=True)
            
        return list_moyennes_globales.index(self.moy_globale()) + 1
    
    def annee_diplome(self):
        annee_encours=int(self.formation.annee_univ.annee_univ)
        annees_restantes=5-self.formation.programme.ordre
        if annees_restantes<0:
            annees_restantes=0
        return str(annee_encours+annees_restantes+1)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['etudiant', 'formation'], name="etudiant-formation")
        ]
    
    def __str__(self):
        return str(self.etudiant) + ' ' + str(self.formation)

class ResidenceUniv(models.Model):
    nom = models.CharField(max_length=50)
    adresse = models.TextField()
    tel = models.CharField(max_length=15, validators=[RegexValidator('^[0-9\+]*$',
                               'Que des chiffres sans espaces et le + pour l\'international')])
    wilaya = models.ForeignKey(Wilaya, on_delete=CASCADE)
    commune = models.ForeignKey(Commune, on_delete=CASCADE)

    def __str__(self):
        return self.nom

def validate_image(fieldfile):
        filesize = fieldfile.file.size
        megabyte_limit = 1.0
        if filesize > megabyte_limit*1024*1024:
            raise ValidationError("Max file size is %sMB" % str(megabyte_limit))  
        #verifier que le nom du fichier ne contient que des caractères qui seront acceptés par l'os
        match=re.match(r"[a-zA-Z0-9_.]+", fieldfile.name)
        if match:
            if match.group() != fieldfile.name:
                raise ValidationError("Le nom du fichier ne doit contenir que les caractères suivants: a-z A-Z 0-9 _.")
        else:
            raise ValidationError("Le nom du fichier ne doit contenir que les caractères suivants: a-z A-Z 0-9 _.")

class Preinscription(models.Model):
    
    inscription = models.OneToOneField(Inscription, on_delete=models.CASCADE)
    wilaya_residence=models.ForeignKey(Wilaya, on_delete=models.CASCADE, null=True, blank=True)
    commune_residence=models.ForeignKey(Commune, on_delete=models.CASCADE, null=True, blank=True)
    interne=models.BooleanField(default=False, null=True, blank=True)
    residence_univ=models.ForeignKey(ResidenceUniv, on_delete=models.SET_NULL, null=True, blank=True)
    adresse_principale=models.TextField(null=True, blank=True)
    photo=models.ImageField(upload_to='tmp',null=True,blank=True, validators=[validate_image])
    quittance=models.ImageField(upload_to='tmp',null=True,blank=True, validators=[validate_image])
    tel=models.CharField(max_length=15, validators=[RegexValidator('^[0-9\+]*$',
                               'Que des chiffres sans espaces et le + pour l\'international')], null=True, blank=True)
    numero_securite_sociale=models.CharField(max_length=15, validators=[RegexValidator('^[0-9\+]*$',
                               'Que des chiffres sans espaces')], null=True, blank=True)

    # i need to delete the temp uploaded file from the file system when i delete this model      
    # from the database
#     def delete(self, using=None):
#         # i ensure that the database record is deleted first before deleting the uploaded 
#         # file from the filesystem.
#         super(Preinscription, self).delete(using)
#         self.photo.close()
#         #self.photo.storage.delete(name_photo)
#         self.photo.delete()
#         self.quittance.close()
#         #self.quittance.storage.delete(name_quittance)    
#         self.quittance.delete()
    
class ReservationPlaceEtudiant(models.Model):
    inscription = models.ForeignKey(Inscription, on_delete=CASCADE)
    seance = models.ForeignKey(Seance, on_delete=CASCADE)
    salle = models.ForeignKey(Salle, on_delete=CASCADE)
    place = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['inscription', 'seance'], name="reservation_place_etudiant")
        ]
    
    def __str__(self):
        return str(self.inscription) + ' : '+str(self.seance.activite.module.matiere.code)+' --> ' + str(self.salle.code)+' ('+str(self.place)+')'

class SurveillanceEnseignant(models.Model):
    enseignant = models.ForeignKey(Enseignant, on_delete=CASCADE)
    seance = models.ForeignKey(Seance, on_delete=CASCADE)
    salle = models.ForeignKey(Salle, on_delete=CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['enseignant', 'seance'], name="surveillance_enseignant")
        ]
    
    def __str__(self):
        return str(self.enseignant) + ' : '+str(self.seance)+' --> ' + str(self.salle.code)

    
class InscriptionPeriode(models.Model):
    inscription=models.ForeignKey(Inscription, on_delete=CASCADE, related_name='inscription_periodes')
    # TODO supprimer cet attribut et le remplacer par periodepgm qui suit
    periode=models.ForeignKey(Periode, on_delete=models.SET_NULL, null=True, blank=True)
    periodepgm=models.ForeignKey(PeriodeProgramme, on_delete=CASCADE, null=True, blank=True)
    groupe=models.ForeignKey(Groupe, on_delete=models.SET_NULL, null=True, blank=True)
    moy=models.DecimalField(max_digits=4, decimal_places=2, default=0)
    #moy_post_delib=models.DecimalField(max_digits=4, decimal_places=2, default=0)
    ne=models.PositiveSmallIntegerField(default=0)
    rang=models.PositiveSmallIntegerField(null=True, blank=True, default=0)
    
    def nb_matieres(self):
        cpt=0
        for ue in self.resultat_ues.all():
            cpt+= ue.resultat_matieres.all().count()
        return cpt
    
    def nb_ne_parmis_matieres(self, matieres_moyenne):
        aggregate=Resultat.objects.filter(inscription=self.inscription, module__matiere__code__in=matieres_moyenne).aggregate(ne=Count('inscription', filter=Q(moy_post_delib__lt=ExpressionWrapper(F('module__note_eliminatoire'), output_field=DecimalField()))))
        return aggregate['ne']

    def nb_ne(self):
        nb_=0
        for ue_ in self.resultat_ues.all():
            for resultat_ in ue_.resultat_matieres.all():
                if resultat_.moy_post_delib < resultat_.module.note_eliminatoire:
                    nb_+=1
        return nb_

    def moyenne(self):
        moy=0
        coef_sum=0
        for resultat_ue in self.resultat_ues.all():
            moy += resultat_ue.moyenne() * resultat_ue.ue.coef()
            coef_sum += resultat_ue.ue.coef()
        if coef_sum!=0:
            return round(moy / coef_sum,2)
        else:
            return 0

    def moyenne_post_delib(self):
        moy=0
        coef_sum=0
        for resultat_ue in self.resultat_ues.all():
            moy += resultat_ue.moyenne_post_delib() * resultat_ue.ue.coef()
            coef_sum += resultat_ue.ue.coef()
        if coef_sum!=0:
            return round(moy / coef_sum,2)
        else:
            return 0

    def moy_post_delib(self):
        # Cette méthode est similaire à la précédente et a été introduite pour garder le code qui se base sur 
        # l'attribut moy_post_delib supprimé
        return self.moyenne_post_delib()

    def moyenne_provisoire(self):
        moy=0
        coef_sum=0
        for resultat_ue in self.resultat_ues.all():
            # on ne compte que les matières suivies dans le semestre prévu dans le programme
            coef = resultat_ue.coef_provisoire()
            moy += resultat_ue.moyenne_provisoire() * coef
            coef_sum += coef
        if coef_sum != 0:
            return round(moy / coef_sum,2)
        else :
            return 0


    def ranking(self):
        aggregate = InscriptionPeriode.objects.filter(inscription__formation=self.inscription.formation, periodepgm=self.periodepgm, moy__gt=self.moy).exclude(groupe__isnull=True).aggregate(ranking=Count('moy'))
        return aggregate['ranking'] + 1

    def credits_requis(self):
        somme=0
        for ue in self.resultat_ues.all():
            somme+=ue.credits_requis()
        return somme   
        
    def credits_obtenus(self):
        somme=0
        if self.moy_post_delib() >= 10:
            for resultat_ue in self.resultat_ues.all():
                for resultat in resultat_ue.resultat_matieres.all():
                    if resultat.moy_post_delib>=resultat.module.note_eliminatoire:
                        somme+=resultat.module.matiere.credit
        else:
            for resultat_ue in self.resultat_ues.all():
                somme+=resultat_ue.credits_obtenus()
        return somme

    def ects_credits(self):
        somme=0
        for resultat_ue in self.resultat_ues.all():
            for resultat in resultat_ue.resultat_matieres.all():
                somme+=resultat.ects_credits()
        return somme

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['inscription', 'periode'], name="inscription-periode")
        ]
    
    def __str__(self):
        return str(self.inscription) + ' ' + str(self.periodepgm)

class ResultatUE(models.Model):
    ue=models.ForeignKey(UE, on_delete=models.SET_NULL, null=True, blank=True)
    inscription_periode=models.ForeignKey(InscriptionPeriode, on_delete=CASCADE, related_name='resultat_ues')
    #TODO à supprimer c'est un champ qu'on recalcule au besoin
    moy=models.DecimalField(max_digits=4, decimal_places=2, default=0)
    #moy_post_delib=models.DecimalField(max_digits=4, decimal_places=2, default=0)
    
    def credits_requis(self):
        somme=0
        for matiere in self.ue.matieres.all():
            somme+=matiere.credit
        return somme   
        
    def credits_obtenus(self):
        somme=0

        if self.moy_post_delib() >= 10:
            
            for resultat in self.resultat_matieres.all():
                if resultat.moy_post_delib>=resultat.module.note_eliminatoire:
                    somme+=resultat.module.matiere.credit
        else:
            for resultat in self.resultat_matieres.all():
                somme+=resultat.credits_obtenus()
        return somme

    def moyenne(self):
        moy=0
        coef_sum=0
        for resultat in self.resultat_matieres.all():
            moy += resultat.moy * resultat.module.matiere.coef
            coef_sum += resultat.module.matiere.coef
        if coef_sum != 0:
            return round(moy / coef_sum,2)
        else:
            return 0

    def moyenne_post_delib(self):
        moy=0
        coef_sum=0
        for resultat in self.resultat_matieres.all():
            moy += resultat.moy_post_delib * resultat.module.matiere.coef
            coef_sum += resultat.module.matiere.coef
        if coef_sum != 0:
            return round(moy / coef_sum,2)
        else:
            return 0
    
    def moy_post_delib(self):
        # Cette méthode est similaire à la précédente et a été introduite pour garder le code qui se base sur 
        # l'attribut moy_post_delib supprimé
        return self.moyenne_post_delib()
        
    def moyenne_provisoire(self):
        moy=0
        coef_sum=0
        for resultat in self.resultat_matieres.all():
            if resultat.module.periode == self.inscription_periode.periodepgm:
                # module suivi au semestre prévu dans le programme
                moy += resultat.moy * resultat.module.matiere.coef
                coef_sum += resultat.module.matiere.coef
        if coef_sum!=0:
            return round(moy / coef_sum,2)
        else:
            return 0
        
    def coef_provisoire(self):
        coef_sum=0
        for resultat in self.resultat_matieres.all():
            if resultat.module.periode == self.inscription_periode.periodepgm:
                # module suivi au semestre prévu dans le programme
                coef_sum += resultat.module.matiere.coef
        return coef_sum
        
    def __str__(self):
        return str(self.ue) + ' ' + str(self.inscription_periode)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['ue', 'inscription_periode'], name="ue-inscription-periode")
        ]
    
class Resultat(models.Model):
    '''
    Résultats d'un module pour un étudiant
    '''
    ECTS=(
        ('A','Excellent: 10%'),
        ('B','Très bien: 25%'),
        ('C','Bien: 30%'),
        ('D','Satisfaisant; 25%'),
        ('E','Passable: 10%'),
        ('Fx','Insuffisant'),
        ('F','Insuffisant'),
    )

    module=models.ForeignKey(Module, on_delete=CASCADE, null=True, blank=True)
    inscription=models.ForeignKey(Inscription, on_delete=CASCADE, null=True, blank=True, related_name='resultats')
    
    moy=models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, default=0)
    # cet attribut devrait disparaître vu que calcul_ects se base sur moy_post_delib
    moy_post_delib=models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, default=0)
    ects=models.CharField(max_length=2, choices = ECTS, default='F', null=True, blank=True)
    # TODO à supprimer on garde uniquement esct_post_delib
    #ects_post_delib=models.CharField(max_length=2, choices = ECTS, default = 'F', null=True, blank=True)
    # pour gérer les redoublants avec des modules acquis, pour éviter de les faire apparaître sur les listes de présence
    acquis=models.BooleanField(default=False)
    resultat_ue=models.ForeignKey(ResultatUE, on_delete=CASCADE, null=True, blank=True, related_name='resultat_matieres')
    
    def credits_obtenus(self):
        if self.moy >= 10:
            return self.module.matiere.credit
        else:
            return 0
        
    def ects_credits(self):
        # cette méthode est obsolète, il faut considérer credits_obtenus qui reflète la réglementation en vigueur
        if self.moy >= self.module.note_eliminatoire:
            return self.module.matiere.credit
        else:
            return 0


    def coef_provisoire(self):
        if self.module.periode == self.resultat_ue.inscription_periode.periodepgm:
            return self.module.matiere.coef
        else:
            return 0
                
    def ranking(self):
        aggregate = Resultat.objects.filter(module=self.module, moy__gt=self.moy).aggregate(ranking=Count('moy'))
        return aggregate['ranking'] + 1
    
    def moyenne(self):
        moy=0
        for note in self.notes.all():
            moy += note.note * note.evaluation.ponderation
        return round(moy,2)

    def calcul_ects(self):
        ects='F'
        # affecter ECTS=F si non acquis
        if self.moy_post_delib < self.module.note_eliminatoire:
            ects='F'
        elif self.moy_post_delib >= self.module.note_eliminatoire and self.moy_post_delib < 10.0:
            #mdoule non acquis avec une moyenne > note éliminatoire
            #ects='Fx'
            ects='F' # on garde F pour tout echec car la note > note_eliminatoire risque d'être trop faible pour avoir Fx
        else:
            # mettre ECST à jour selon ranking dans le module
            nb_inscrits_module=Resultat.objects.filter(module=self.module, moy_post_delib__gte=10.0).count()
            rang=self.ranking()
            if  rang <= nb_inscrits_module * decimal.Decimal(0.10):
                ects='A'
            elif rang <= nb_inscrits_module * decimal.Decimal(0.10 + 0.25):
                ects='B'
            elif rang <= nb_inscrits_module * decimal.Decimal(0.10 + 0.25 + 0.30):
                ects='C'
            elif rang <= nb_inscrits_module * decimal.Decimal(0.10 + 0.25 + 0.30 + 0.25):
                ects='D'
            else :
                ects='E'
        return ects
                    
    

    def __str__(self):
        return str(self.inscription.etudiant) + ' ' + str(self.module)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['inscription', 'module'], name="inscription-module")
        ]
    
    
class Note(models.Model):
    '''
    Une note correspondant à une évaluation prévue dans un module
    '''
    note=models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    note_post_delib=models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    evaluation=models.ForeignKey(Evaluation, on_delete=CASCADE, null=True, blank=True)
    resultat=models.ForeignKey(Resultat, on_delete=CASCADE, null=True, blank=True, related_name='notes')
    def __str__(self):
        return str(self.resultat) + ' ' + str(self.evaluation) + ' ' + str(self.note)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['evaluation', 'resultat'], name="evaluation-resultat")
        ]

class GoogleCalendar(models.Model):
    code = models.CharField(max_length=20)
    calendarId = models.CharField(max_length=100)

    def __str__(self):
        return self.code
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['code'], name="gcal-code")
        ]
    
TYPE_ORGANISME=(
    ('R','Laboratoire / Centre de Recherche'),
    ('E', 'Entreprise'),
    ('A','Administration'),
)

NATURE_ORGANISME=(
    ('P','Publique'),
    ('PR', 'Privée'),
    ('M','Mixte'),
)

STATUT_ORGANISME=(
    ('SPA','Société Par Actions'),
    ('SARL', 'Société Anonyme à Résponsabilité Limitée'),
    ('EURL','Entreprise Unanime à Résponsabilité Limitée'),
)

TAILLE_ORGANISME=(
    ('10','Moins de 10 salariés'),
    ('100', 'Entre 10 et 100 salariés'),
    ('500','Entre 100 et 500 salariés'),
    ('1000','Plus de 500 salariés'),
)

SECTEUR_ORGANISME=(
    ('S','Services'),
    ('C', 'Commercial'),
    ('I','Industriel'),
)

class Organisme(models.Model):
    sigle = models.CharField(max_length=50, primary_key=True, validators=[RegexValidator('^[A-Z_\-\&\@\ 0-9]+$',
                               'Saisir en majuscule')])
    nom = models.CharField(max_length=200)
    adresse = models.TextField(null=True, blank=True)
    pays=models.ForeignKey(Pays, on_delete=CASCADE, default='DZ')
    type=models.CharField(max_length=2, choices=TYPE_ORGANISME)
    nature=models.CharField(max_length=2, choices=NATURE_ORGANISME, null=True, blank=True)
    statut=models.CharField(max_length=5, choices=STATUT_ORGANISME, null=True, blank=True)
    taille=models.CharField(max_length=5, choices=TAILLE_ORGANISME, null=True, blank=True) 
    secteur=models.CharField(max_length=2, choices=SECTEUR_ORGANISME, null=True, blank=True) 
    
    def __str__(self):
        return str(self.sigle)+' : '+self.nom

#     class Meta:
#         constraints = [
#             models.UniqueConstraint(fields=['sigle'], name="sigle-organisme"),
#         ]
    
STATUT_VALIDATION=(
    ('S', 'Soumis'),
    ('W', 'Validation en cours'),
    ('RR', 'Révision Requise'),
    ('RT', 'Révision Terminée'),
    ('LR', 'Levée de Réserve'),
    ('V', 'Validé'),
    ('N', 'Rejeté'),
)

TYPE_STAGE=(
        ('P', 'PFE'),
        ('M', 'Master')
    )
OPTION_MOYENS=(
        ('ESI','A la charge de l\'école'),
        ('ORG','A la charge de l\'organisme d\'accueil')
    )
class PFE(models.Model):
    type = models.CharField(max_length=2, choices=TYPE_STAGE, default='P')
    specialites = models.ManyToManyField(Specialite)
    organisme = models.ForeignKey(Organisme, on_delete=models.SET_NULL, null=True)
    groupe = models.OneToOneField(Groupe, on_delete=CASCADE, null=True, blank=True)
    coencadrants = models.ManyToManyField(Enseignant, blank=True, related_name='pfes')
    promoteur = models.TextField(max_length=100, null=True)
    email_promoteur = models.EmailField(null=True)
    tel_promoteur = models.CharField(max_length=20, null=True, blank=True, validators=[RegexValidator('^[0-9\+]*$',
                               'Que des chiffres sans espaces et le + pour l\'international')])
    intitule = models.TextField(null=True)
    resume = models.TextField(null=True)
    objectifs = models.TextField(null=True)
    resultats_attendus = models.TextField(null=True)
    antecedents = models.TextField(null=True, blank=True)
    moyens_informatiques = models.CharField(max_length=3, choices=OPTION_MOYENS, null=True, blank=True)
    echeancier = models.TextField(null=True)
    bibliographie = models.TextField(null=True, blank=True)
    statut_validation = models.CharField(max_length=2, choices=STATUT_VALIDATION, default='S')
    reponse_aux_experts = models.TextField(null=True, blank=True)
    reserve_pour = models.ManyToManyField(Inscription)
    projet_recherche = models.CharField(max_length=200, null=True, blank=True)
    # cet attribut sert à bloquer les notifications après la validation du sujet suite à de nouvelles modifications
    notification = models.BooleanField(default=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['groupe'], name="groupe-pfe"),
        ]
        
    def nb_avis(self):
        return Validation.objects.filter(pfe=self.id).exclude(avis='X').count()
    
    def __str__(self):
        if self.groupe:
            return str(self.groupe) +' '+self.intitule
        else:
            return self.intitule

OPTIONS_VALIDATION=(
    ('V', 'Avis favorable'),
    ('SR', 'Avis favorable avec réserves mineures'),
    ('MR', 'Avis favorable avec réserves majeures'),
    ('N', 'Avis défavorable'),
    ('X','Non Renseigné'),
)

class Validation(models.Model):
    pfe = models.ForeignKey(PFE, on_delete=CASCADE, related_name='validations')
    expert = models.ForeignKey(Enseignant, on_delete=CASCADE)
    avis = models.CharField(max_length=2, choices=OPTIONS_VALIDATION, default='X')
    commentaire=models.TextField(null=True, blank=True)
    debut=models.DateField(null=True, blank=True)
    fin=models.DateField(null=True)
    
#     class Meta:
#         constraints = [
#             models.UniqueConstraint(fields=['pfe','expert', 'avis'], name="pfe-expert-avis")
#         ]

    

class Question(models.Model):
    code=models.CharField(max_length=3, primary_key=True)
    intitule=models.CharField(max_length=80)   
    projet_na=models.BooleanField(default=False)
    cours_na=models.BooleanField(default=False)         
    def __str__(self):
        return str(self.code) +' : '+ str(self.intitule)

class Feedback(models.Model):
    
    module=models.ForeignKey(Module, on_delete=CASCADE, related_name='feedbacks')
    inscription=models.ForeignKey(Inscription, on_delete=CASCADE, null=True, blank=True)
    comment=models.TextField(null=True, blank=True)
    show=models.BooleanField(default=True)
    def __str__(self):
#         if self.resultat:
#             return str(self.module.matiere.code) +' by '+str(self.resultat.etudiant)
#         else : 
        return str(self.module.matiere.code) +' by anonymous'

class Reponse(models.Model):
    REPONSE=(
        ('++','Tout à fait d\'accord'),
        ('+','D\'accord'),
        ('-','Pas d\'accord'),
        ('--','En total désaccord'),
    )
    feedback=models.ForeignKey(Feedback, on_delete=CASCADE, related_name='reponses')
    question=models.ForeignKey(Question, on_delete=CASCADE)
    reponse=models.CharField(max_length=2, choices=REPONSE)
    def __str__(self):
        return str(self.question)+ ' ' +str(self.feedback) 

class CompetenceFamily(models.Model):
    code=models.CharField(max_length=5, primary_key = True)
    intitule = models.CharField(max_length = 120)
    def __str__(self):
        return self.code + ' : ' + self.intitule

class Competence(models.Model):
    code = models.CharField(max_length = 10)
    competence_family = models.ForeignKey(CompetenceFamily, on_delete = CASCADE, null = True, related_name='competences')
    intitule = models.CharField(max_length = 160)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['code', 'competence_family'], name="competence-competence-family")
        ]
    def __str__(self):
        return self.code + ' : ' + self.intitule

class CompetenceElement(models.Model):

    TYPE=(
        ('MOD','Modélisation'),
        ('MET','Méthodologie'),
        ('TEC','Technique'),
        ('OPE','Opérationnel'),        
    )

    code = models.CharField(max_length = 10)
    competence = models.ForeignKey(Competence, on_delete=CASCADE, null=True, related_name='competence_elements')
    intitule = models.CharField(max_length = 160)
    type = models.CharField(max_length = 5, choices = TYPE)
    objectif = models.TextField(null=True, blank=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['code', 'competence'], name="competence-element-competence")
        ]
    def __str__(self):
        return self.code + ' : ' + self.intitule
    
class MatiereCompetenceElement(models.Model):
    NIVEAU=(
        ('B','Base'),
        ('I','Intermédiaire'),
        ('A','Avancé'),
    )
    matiere = models.ForeignKey(Matiere, on_delete=CASCADE, null=True)
    competence_element = models.ForeignKey(CompetenceElement, on_delete=CASCADE, null=True, related_name='competence_elements')
    niveau = models.CharField(max_length = 1, choices = NIVEAU)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['matiere', 'competence_element'], name="matiere-competence-element")
        ]
        
        indexes = [models.Index(fields=['matiere','competence_element'])]
        
    def __str__(self):
        return str(self.matiere) + ' : ' + str(self.competence_element)
    
class Semainier(models.Model):
    SEMAINE=(
        (1, 'Semaine 1'),
        (2, 'Semaine 2'),
        (3, 'Semaine 3'),
        (4, 'Semaine 4'),
        (5, 'Semaine 5'),
        (6, 'Semaine 6'),
        (7, 'Semaine 7'),
        (8, 'Semaine 8'),
        (9, 'Semaine 9'),
        (10, 'Semaine 10'),
        (11, 'Semaine 11'),
        (12, 'Semaine 12'),
        (13, 'Semaine 13'),
        (14, 'Semaine 14'),
        (15, 'Semaine 15')
    )    
    module=models.ForeignKey(Module, on_delete=CASCADE)
    semaine=models.PositiveSmallIntegerField(choices=SEMAINE)
    activite_cours=models.CharField(max_length=255, null=True, blank=True)
    activite_dirigee=models.TextField(null=True, blank=True)
    observation=models.CharField(max_length=255, null=True, blank=True)
    objectifs=models.CharField(max_length=255, null=True, blank=True)
    matiere_competence_element=models.ForeignKey(MatiereCompetenceElement, on_delete=models.SET_NULL, null=True, blank=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['module', 'semaine'], name="module-semaine")
        ]
    def __str__(self):
        return str(self.module.matiere.code) + ' : ' + str(self.semaine)
    
class EvaluationCompetenceElement(models.Model):
    evaluation=models.ForeignKey(Evaluation, on_delete=CASCADE, related_name='competence_elements')
    competence_element=models.ForeignKey(CompetenceElement, on_delete=CASCADE)
    commune_au_groupe=models.BooleanField(default=False)
    ponderation=models.DecimalField(max_digits=4, decimal_places=2, default=0)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['evaluation', 'competence_element'], name="evaluation_competence_element")
        ]
    def __str__(self):
        return str(self.evaluation.type) + ' : ' + str(self.competence_element.intitule)

class NoteCompetenceElement(models.Model):
    evaluation_competence_element=models.ForeignKey(EvaluationCompetenceElement, on_delete=CASCADE, null=True, blank=True)
    note_globale=models.ForeignKey(Note, on_delete=CASCADE, null=True, blank=True) #Note globale à laquelle contribue cette note d'un élément de compétence
    valeur=models.DecimalField(max_digits=4, decimal_places=2, default=0) # pour obtenir les points attribués: valeur * eval_competence_element.ponderation * 20
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['evaluation_competence_element','note_globale'], name="evaluation_competence_element_note_globale")
        ]

################################################# MODELS Reget

class Regisseur(models.Model):
        user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
        nom = models.CharField(max_length=50)
        eps = models.CharField(max_length=50, null=True, blank=True)
        prenom = models.CharField(max_length=50)
        nom_a = models.CharField(max_length=50, null=True, blank=True)
        eps_a = models.CharField(max_length=50, null=True, blank=True)
        prenom_a = models.CharField(max_length=50, null=True, blank=True)
        sexe = models.CharField(max_length=1, choices=SEXE, null=True, blank=True)
        tel = models.CharField(max_length=15, null=True, blank=True)
        bureau = models.CharField(max_length=10, null=True, blank=True)


class Chapitre(models.Model):
        code_chap = models.CharField(max_length=10)
        libelle_chap_FR = models.CharField(max_length=100)
        libelle_chap_AR = models.CharField(max_length=100, null=True, blank=True)

class Article(models.Model):
        code_art = models.CharField(max_length=10)
        chapitre = models.ForeignKey(Chapitre, on_delete=CASCADE, default='', related_name="articles")
        libelle_art_FR = models.CharField(max_length=100)
        libelle_art_AR = models.CharField(max_length=100, null=True, blank=True)
       

class Credit(models.Model):
        article = models.ForeignKey(Article, on_delete=CASCADE)
        chapitre = models.ForeignKey(Chapitre, on_delete=CASCADE)
        credit_allouee = MoneyField(decimal_places=2, max_digits=9, default_currency='DZD')
        credit_reste = MoneyField(decimal_places=2, max_digits=9, default_currency='DZD')
        class Meta:
         constraints = [
            models.UniqueConstraint(fields=['chapitre', 'article'], name="chapitre-article")
        ]

class Bordereau(models.Model):
        credit = models.ForeignKey(Credit, on_delete=CASCADE, default='')
        deseingnation = models.CharField(max_length=200, null=True, blank=True)
        regisseur = models.CharField(max_length=50, null=True, blank=True)
        cloture = models.BooleanField(default=False)

class Piece(models.Model):
        credit = models.ForeignKey(Credit, on_delete=CASCADE, default='')
        bordreau = models.ForeignKey(Bordereau, on_delete=CASCADE, default='')
        deseingnation = models.CharField(max_length=200, null=True, blank=True)
        montant = MoneyField(decimal_places=2, max_digits=9, default_currency='DZD')




