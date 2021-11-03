from django import forms
from scolar.models import *
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Div, Field, HTML
from django.shortcuts import get_object_or_404
from crispy_forms.layout import Submit, Button, Hidden
from crispy_forms.bootstrap import TabHolder, Tab, FormActions
from django.urls import reverse
from django_select2.forms import ModelSelect2Widget, Select2Widget, ModelSelect2MultipleWidget, Select2MultipleWidget
from bootstrap_datepicker_plus import DatePickerInput, TimePickerInput, DateTimePickerInput
import datetime
from scolar.models import Chapitre, Article

from string import Template
from django.utils.safestring import mark_safe

from django.contrib import messages
from scolar.admin import settings




class ImportChargeForm(forms.ModelForm):
    
    class Meta:
        model = Charge
        fields = ['annee_univ', 'periode', 'type', 'obs', 'repeter_chaque_semaine']
    
    def __init__(self, *args, **kwargs):
        super(ImportChargeForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.fields['file']=forms.FileField(label='Choisir un fichier', widget=forms.FileInput(attrs={'class':"custom-file-input"}))
        self.helper.add_input(Submit('submit','Importer',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))

        self.helper.form_method='POST'
    
    
class ChargeFilterForm(forms.Form):

    enseignant_list = forms.ModelMultipleChoiceField(
            queryset=Enseignant.objects.filter(situation='A').order_by('nom', 'prenom'),
            label=u"Enseignants",
            widget=ModelSelect2MultipleWidget(
                    model=Enseignant,
                    search_fields=['nom__icontains','prenom__icontains'],
                ),
            help_text = "Sélection multiple possible. Tapez le nom ou prénom de l'enseignant ou deux espaces pour avoir la liste complète.",
            required = False
        )

    charge_inf = forms.DecimalField(
            label=u"Ratio >= ?? %",
            help_text = "Tapez le ratio en %",
            max_digits=5, decimal_places=2,
            required = False
        )
    
    charge_sup = forms.DecimalField(
            label=u"Ratio <= ?? %",
            help_text = "Tapez le ratio en %",
            max_digits=5, decimal_places=2,
            required = False
        )

    def __init__(self, *args, **kwargs):
        super(ChargeFilterForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.layout = Layout(
            Div(
                Div(
                    'enseignant_list', 'charge_inf', 'charge_sup',
                    css_class='row'
                ), css_class="col-lg-12"
            ),
            FormActions(
                Submit('submit', 'Filtrer'),
                HTML('<a class="btn btn-info" href="{% url "charge_batch_create" %}">Importer des Charges</a>'),
                HTML('<a class="btn btn-secondary" href="{% url "home" %}">Annuler</a>')
            )
        )

        self.helper.form_method='POST'
        

class EDTForm(forms.Form):
    groupe_list=[(x.id, x ) for x in Groupe.objects.filter(section__formation__annee_univ__encours=True, code__isnull=False).order_by('section__formation__programme__ordre','code')]
    groupe = forms.ChoiceField(
            choices=groupe_list,
            label=u"Groupe",
            widget = Select2Widget(),
            required = False,
            help_text = "Tapez le code du groupe ou deux espaces pour avoir la liste complète.",
            )

    etudiant = forms.ModelChoiceField(
            queryset=Etudiant.objects.all().order_by('nom', 'prenom'),
            label=u"Etudiant",
            widget=ModelSelect2Widget(
                    model=Etudiant,
                    search_fields=['nom__icontains', 'prenom__icontains',],

                ),
            help_text = "Tapez le nom ou prénom d'un étudiant ou deux espaces pour avoir la liste complète.",
            required = False
        )
    enseignant = forms.ModelChoiceField(
            queryset=Enseignant.objects.all().order_by('nom', 'prenom'),
            label=u"Enseignant",
            widget=ModelSelect2Widget(
                    model=Enseignant,
                    search_fields=['nom__icontains', 'prenom__icontains',],

                ),
            help_text = "Tapez le nom ou prénom d'un enseignant ou deux espaces pour avoir la liste complète.",
            required = False
        )

    def __init__(self, *args, **kwargs):
        super(EDTForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Submit('submit','Trouver',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))

        self.helper.form_method='POST'


class CommissionValidationCreateForm(forms.Form):

    def __init__(self, pfe_pk, *args, **kwargs):
        super(CommissionValidationCreateForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        pfe_=get_object_or_404(PFE, id=pfe_pk)
        self.fields['pfe'] = forms.ModelChoiceField(disabled=True, queryset=PFE.objects.filter(id=pfe_pk), initial=pfe_pk)
        self.fields['promoteur'] = forms.CharField(disabled=True, initial=pfe_.promoteur)
        self.fields['coencadrants'] = forms.ModelMultipleChoiceField(
                label="Coencadrants",
                queryset = Enseignant.objects.all().order_by('nom', 'prenom'),
                initial=pfe_.coencadrants.all(),
                widget=ModelSelect2MultipleWidget,
                disabled=True,
                required=False
            )
        enseignant_nb_avis_list=[] 
        for enseignant_ in Enseignant.objects.all().order_by('nom','prenom'):
            enseignant_nb_avis_list.append((enseignant_.id, str(enseignant_)+" Sollicitations("+str(enseignant_.nb_avis())+") Vides("+str(enseignant_.nb_avis_vides())+")"))
        self.fields['experts'] = forms.MultipleChoiceField(
                label="Membres de la commission",
                choices=enseignant_nb_avis_list,
                widget=Select2MultipleWidget,
                help_text = "Vous pouvez séléctionner plusieurs enseignants. Tapez un nom ou prénom ou 2 espaces pour avoir la liste complète.",
                required = True
                
            )
        self.fields['fin'] = forms.DateField(label='Echéance', input_formats = settings.DATE_INPUT_FORMATS, widget=DatePickerInput(format='%d/%m/%Y'), initial=datetime.date.today())
        self.helper.add_input(Submit('submit','Créer commission',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.helper.form_method='POST'
    
class CompetenceForm(forms.Form):
    competence_family = forms.ChoiceField(
            choices=CompetenceFamily.objects.values_list(),
            label=u"Famille de Compétences",
            widget = Select2Widget(attrs={'style':'width:800px; height:10px;'}),
            required = False,
            help_text = "Tapez un mot clé ou deux espaces pour avoir la liste complète.",
            )
    competence = forms.ModelChoiceField(
            queryset=Competence.objects.all().order_by('code'),
            label=u"Compétences",
            widget=ModelSelect2Widget(
                    model=Competence,
                    search_fields=['intitule__icontains',],
                    dependent_fields={'competence_family':'competence_family'},
                    attrs={'style':'width:800px; height:10px;'}
                ),
            help_text = "Tapez un mot clé ou deux espaces pour avoir la liste complète.",
            required = False
        )
    competence_element = forms.ModelMultipleChoiceField(
            queryset=CompetenceElement.objects.all().order_by('code'),
            label=u"Eléments de Compétences",
            widget=ModelSelect2MultipleWidget(
                    model=CompetenceElement,
                    search_fields=['intitule__icontains',],
                    dependent_fields={'competence':'competence'},
                    attrs={'style':'width:800px; height:10px;'}
                ),
            help_text = "Vous pouvez séléctionner plusieurs éléments de compétence. Tapez un mot clé ou 2 espaces pour avoir la liste complète.",
            required = False
        )
    def __init__(self, *args, **kwargs):
        super(CompetenceForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Submit('submit','Ajouter',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.helper.add_input(Hidden('form_type','filtre'))
        self.helper.form_method='POST'

TYPE_DOC=(
    ('C3L', 'Certificats de Scolarité Trilingues'),
    ('C2L', 'Certificats de Scolarité Bilingues'),
    ('RP1', 'Relevés Provisoires S1'),
    ('RP2', 'Relevés Provisoires S2'),
    ('RA', 'Relevés Annuels'),
    ('RECTS', 'Relevés ECTS'),
    ('FPFE', 'Fiches PFE'),
)

class SelectionFormationForm(forms.Form):
    annee_univ = forms.ChoiceField(
            choices=AnneeUniv.objects.all().values_list('annee_univ','annee_univ').order_by('-annee_univ'),
            label=u"Année Universitaire",
            widget = Select2Widget(attrs={'style':'width:800px; height:10px;'}),
            required = True,
            help_text = "Choisir l'année universitaire.",
            )
    formation = forms.ModelChoiceField(
            queryset=Formation.objects.all().order_by('programme__ordre'),
            label=u"Formation",
            widget=ModelSelect2Widget(
                    model=Formation,
                    search_fields=['programme__code__icontains',],
                    dependent_fields={'annee_univ':'annee_univ'},
                    attrs={'style':'width:800px; height:10px;'}
                ),
            help_text = "Choisir l'année d'étude ou spécialité. Tapez deux espaces pour avoir toute la liste.",
            required = True
        )
    type_document = forms.ChoiceField(
            choices=TYPE_DOC,
            label=u"Type de Document",
            widget=Select2Widget(attrs={'style':'width:800px; height:10px;'}),
            help_text = "Choisir le type de documents groupés à générer",
            required = True
        )
    periode = forms.ChoiceField(
            choices=Periode.objects.all().values_list('id','code').order_by('ordre'),
            label=u"Semestre",
            widget = Select2Widget(attrs={'style':'width:800px; height:10px;'}),
            required = False,
            help_text = "Choisir le semestre si le document est semestriel",
            )
    def __init__(self, *args, **kwargs):
        super(SelectionFormationForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Submit('submit','Générer',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.helper.form_method='POST'

class SelectionInscriptionForm(forms.Form):
    annee_univ = forms.ChoiceField(
            choices=AnneeUniv.objects.all().values_list('annee_univ','annee_univ').order_by('-annee_univ'),
            label=u"Année Universitaire",
            widget = Select2Widget(
                #attrs={'style':'width:800px; height:10px;'}
                ),
            required = True,
            help_text = "Choisir l'année universitaire.",
            )
    formation = forms.ModelChoiceField(
            queryset=Formation.objects.all().order_by('programme__ordre'),
            label=u"Formation",
            widget=ModelSelect2Widget(
                    model=Formation,
                    search_fields=['programme__code__icontains',],
                    dependent_fields={'annee_univ':'annee_univ'},
                    #attrs={'style':'width:800px; height:10px;'}
                ),
            help_text = "Choisir l'année d'étude ou spécialité. Tapez deux espaces pour avoir toute la liste.",
            required = True
        )
    inscription = forms.ModelChoiceField(
            queryset=Inscription.objects.filter(decision_jury='X').order_by('etudiant__nom', 'etudiant__prenom'),
            label=u"Etudiant",
            widget=ModelSelect2Widget(
                    model=Inscription,
                    search_fields=['etudiant__nom__icontains', 'etudiant__prenom__icontains',],
                    dependent_fields={'formation':'formation'},
                    #attrs={'style':'width:800px; height:10px;'}
                ),
            help_text = "Choisir l'étudiant à inscrire. Tapez le nom ou le prénom.",
            required = True
        )

    def __init__(self, *args, **kwargs):
        super(SelectionInscriptionForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Submit('submit','Inscrire',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.helper.form_method='POST'


class ValidationPreInscriptionForm(forms.Form):

#     valider_wilaya_residence = forms.BooleanField(initial=False, required=False)
#     valider_commune_residence = forms.BooleanField(initial=False, required=False)
#     valider_adresse_principale = forms.BooleanField(initial=False, required=False)
#     valider_tel = forms.BooleanField(initial=False, required=False)
#     valider_photo = forms.BooleanField(initial=False, required=False)
#     valider_quittance = forms.BooleanField(initial=False, required=False)
#     valider_interne = forms.BooleanField(initial=False, required=False)
#     valider_residence_univ = forms.BooleanField(initial=False, required=False)
#     valider_numero_securite_sociale = forms.BooleanField(initial=False, required=False)
    CHOIX_VALIDATION=(
            ('V', "Inscription valide: les informations sont cohérentes et quittance de payement des frais d'inscription présente."),
            ('N', "Inscription non valide: dossier incomplet.")
        )
    valider_inscription = forms.ChoiceField(label="Validation", 
                                            choices=CHOIX_VALIDATION, 
                                            initial='N', 
                                            required=True,
                                            widget=forms.RadioSelect(),)
    motif_refus = forms.CharField(max_length=1000, widget=forms.Textarea(), required=False,
                                  help_text="Remplir dans le cas de refus pour expliquer les raisons du refus.")
        
    def __init__(self, *args, **kwargs):
        super(ValidationPreInscriptionForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
         
         
        self.helper.add_input(Submit('submit','Envoyer',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.helper.form_method='POST'


class AbsenceEtudiantReportSelectionForm(forms.Form):
    formation = forms.ModelChoiceField(
            queryset=Formation.objects.filter(annee_univ__encours=True).order_by('programme__ordre'),
            label=u"Formation",
            widget=ModelSelect2Widget(
                    model=Formation,
                    search_fields=['programme__code__icontains',],
                ),
            help_text = "Choisir l'année d'étude ou spécialité. Tapez deux espaces pour avoir toute la liste.",
            required = True
        )
    periode = forms.ChoiceField(
            choices=Periode.objects.all().values_list('id','code').order_by('ordre'),
            label=u"Semestre",
            widget = Select2Widget,
            required = True,
            help_text = "Choisir le semestre",
            )
    
    type_activite_list = forms.MultipleChoiceField(
            choices=TYPES_ACT,
            label=u"Type d'Activité Pédagogique",
            widget=Select2MultipleWidget,
            help_text = "Choisir les types d'activités",
            required = True
        )
    def __init__(self, *args, **kwargs):
        super(AbsenceEtudiantReportSelectionForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Submit('submit','Générer',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.helper.form_method='POST'
    

class MatiereCompetenceForm(forms.Form):
    def __init__(self, matiere_pk, *args, **kwargs):
        super(MatiereCompetenceForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.fields['competence_element'] = forms.MultipleChoiceField(
            choices=CompetenceElement.objects.filter(competence_elements__matiere=matiere_pk).values_list('id','intitule'),
            label=u"Eléments de Compétences",
            widget=Select2MultipleWidget,
            help_text = "Vous pouvez séléctionner plusieurs éléments de compétence. Tapez un mot clé ou 2 espaces pour avoir la liste complète.",
            required = False
        )

        self.helper.add_input(Submit('submit','Ajouter',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.helper.add_input(Hidden('form_type','filtre'))
        self.helper.form_method='POST'


class SelectChargeConfigForm(forms.Form):
    charge_config = forms.ModelChoiceField(
            queryset=ActiviteChargeConfig.objects.all().order_by('categorie', 'type'),
            label=u"Modèle de Charge",
            help_text = "Choisir un modèle de charge dans la liste",
            )
    periode = forms.ModelChoiceField(
            queryset=Periode.objects.all().order_by('code'),
            label=u"Semestre",
            )
    obs = forms.CharField(
            max_length=50,
            label=u"Observation",
            help_text = "Complément d'information concernant cette charge, par ex. Nom du Doctorant qui va soutenir",
        )
    
    def __init__(self, *args, **kwargs):
        super(SelectChargeConfigForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Submit('submit','Ajouter',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))

        self.helper.form_method='POST'

class ExamenCreateForm(forms.Form):
    type_activite = forms.ChoiceField(
            choices= TYPES_ACT_EXAM,
            label=u"Type Examen",
            widget = Select2Widget
            ) 
    date = forms.DateField(input_formats = settings.DATE_INPUT_FORMATS, widget=DatePickerInput(format='%d/%m/%Y'), initial=datetime.date.today()) # 

    heure_debut = forms.TimeField(input_formats=['%H:%M'], widget=TimePickerInput(format='%H:%M')) #
    
    duree = forms.TimeField(input_formats=['%H:%M'], widget=TimePickerInput(format='%H:%M')) 

    
    def __init__(self, *args, **kwargs):
        super(ExamenCreateForm, self).__init__(*args, **kwargs)
        
        self.helper=FormHelper()
        
        self.fields['formation'] = forms.ModelChoiceField(
            queryset=Formation.objects.filter(annee_univ__encours=True).order_by('programme__ordre'),
            label=u"Formation",
            widget=ModelSelect2Widget(
                    model=Formation,
                    search_fields=['programme__code__icontains'],
                ),
            help_text = "Indiquez la formation concernée. Tapez le code de la formation (ex. 2ST), ou 2 espaces pour avoir la liste complète.",
            required = True
        )
        self.fields['periode'] = forms.ModelChoiceField(
            queryset=Periode.objects.all().order_by('code'),
            label=u"Période",
            widget=ModelSelect2Widget(
                    model=Periode,
                    search_fields=['code__icontains'],
                ),
            help_text = "Indiquez la période concernée. Tapez le code de la période (ex. S1), ou 2 espaces pour avoir la liste complète.",
            required = True
        )
        self.fields['module'] = forms.ModelChoiceField(
            queryset=Module.objects.filter(formation__annee_univ__encours=True).order_by('matiere__code'),
            label=u"Module",
            widget=ModelSelect2Widget(
                    model=Module,
                    search_fields=['matiere__code__icontains'],
                    dependent_fields={'formation':'formation', 'periode':'periode__periode'},
                ),
            help_text = "Indiquez la période concernée. Tapez le code de la période (ex. S1), ou 2 espaces pour avoir la liste complète.",
            required = True
        )

        self.fields['groupes'] = forms.ModelMultipleChoiceField(
            queryset=Groupe.objects.filter(section__formation__annee_univ__encours=True, code__isnull=False).order_by('code'),
            label=u"Groupes concernés",
            widget=ModelSelect2MultipleWidget(
                    model=Groupe,
                    search_fields=['code__icontains'],
                    dependent_fields={'formation':'section__formation'},
                ),
            help_text = "Indiquez les groupes. Tapez le code du groupe (ex. G09), ou 2 espaces pour avoir la liste complète.",
            required = True
        )     
        self.helper.add_input(Submit('submit','Créer',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))

        self.helper.form_method='POST'

class SeanceSallesReservationForm(forms.Form):
        
    def __init__(self, seance_pk, *args, **kwargs):
        super(SeanceSallesReservationForm, self).__init__(*args, **kwargs)
        
        seance_=get_object_or_404(Seance, id=seance_pk)
        
        
        self.helper=FormHelper()
        
        self.fields['seance'] = forms.ModelChoiceField(
                queryset=Seance.objects.all(),
                initial=seance_
            )
        self.fields['seance'].widget.attrs['readonly']=True
        
        self.fields['groupes'] = forms.ModelMultipleChoiceField(
            queryset = Groupe.objects.all(),
            initial= seance_.activite.cible.all(),
            label=u"Groupes concernés",
            widget=ModelSelect2MultipleWidget(
                model = Groupe),
        )
        
        self.fields['groupes'].widget.attrs['readonly']=True 
        
        self.fields['capacite_requise'] = forms.IntegerField(initial=seance_.activite.nb_etudiants())
        self.fields['capacite_requise'].widget.attrs['readonly']=True 

        self.fields['capacite_reservee'] = forms.IntegerField(initial=0)
        self.fields['capacite_reservee'].widget.attrs['readonly']=True 
        
        seance_chevauchement_list=Seance.objects.filter(date=seance_.date).exclude(
                                                                            heure_debut__gt=seance_.heure_fin
                                                                        ).exclude(
                                                                            heure_fin__lt=seance_.heure_debut
                                                                        )
        salle_occupee_list=[]
        for seance_chevauchement_ in seance_chevauchement_list:
            for salle_occupee_ in seance_chevauchement_.salles.all():
                if not salle_occupee_ in salle_occupee_list:
                    salle_occupee_list.append(salle_occupee_)
         
        salle_disponible_capacite_list=[]
        for salle_ in Salle.objects.all().order_by('code'):
            if not salle_ in salle_occupee_list:
                salle_disponible_capacite_list.append((salle_.id, str(salle_.code)+' : '+str(salle_.capacite()))) 
        
        self.fields['salles'] = forms.MultipleChoiceField(
            choices = salle_disponible_capacite_list,
            label=u"Salles réservées",
            widget=Select2MultipleWidget(attrs={'onchange':'update_capacite_reservee();'}
                ),
            help_text = "Indiquez les salles à réserver.",
            required = True
        )

             
        self.helper.add_input(Submit('submit','Réserver',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))

        self.helper.form_method='POST'

class SurveillanceUpdateForm(forms.Form):
        
    def __init__(self, seance_pk, *args, **kwargs):
        super(SurveillanceUpdateForm, self).__init__(*args, **kwargs)
        
        seance_=get_object_or_404(Seance, id=seance_pk)
        
        
        self.helper=FormHelper()
        
        self.fields['seance'] = forms.ModelChoiceField(
                queryset=Seance.objects.all(),
                initial=seance_
            )
        self.fields['seance'].widget.attrs['readonly']=True
        
        self.fields['groupes'] = forms.ModelMultipleChoiceField(
            queryset = Groupe.objects.all(),
            initial= seance_.activite.cible.all(),
            label=u"Groupes concernés",
            widget=ModelSelect2MultipleWidget(
                model = Groupe),
        )
        self.fields['groupes'].widget.attrs['readonly']=True 

        seance_chevauchement_list=Seance.objects.filter(date=seance_.date).exclude(
                                                                            heure_debut__gt=seance_.heure_fin
                                                                        ).exclude(
                                                                            heure_fin__lt=seance_.heure_debut
                                                                        )
        enseignant_occupe_list=[]
        for seance_chevauchement_ in seance_chevauchement_list:
            for enseignant_occupe_ in seance_chevauchement_.activite.assuree_par.all():
                if not enseignant_occupe_ in enseignant_occupe_list:
                    enseignant_occupe_list.append(enseignant_occupe_)
        
        
        enseignant_charge_list=[] 
        for enseignant_ in Enseignant.objects.all().order_by('nom','prenom'):
            if not enseignant_ in enseignant_occupe_list: 
                enseignant_charge_list.append((enseignant_.id, str(enseignant_)+" (Charge= "+str(enseignant_.ratio_charge_annuelle_encours())+"% )"))
        
        for salle_ in seance_.salles.all().order_by('code'):
            self.fields[salle_.code] = forms.MultipleChoiceField(
                label="Surveillants affectés à la salle: "+salle_.code,
                choices=enseignant_charge_list,
                widget=Select2MultipleWidget,
                help_text = "Vous pouvez séléctionner plusieurs enseignants. Tapez un nom ou prénom ou 2 espaces pour avoir la liste complète.",
                required = True
            )
             
        self.helper.add_input(Submit('submit','Affecter',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))

        self.helper.form_method='POST'

class ExamenSelectForm(forms.Form):
    formation_list = forms.ModelMultipleChoiceField(
            queryset=Formation.objects.filter(annee_univ__encours=True).order_by('programme__ordre'),
            label=u"Formations concernées par l'envoi des convocations",
            widget=ModelSelect2MultipleWidget(
                model=Formation,
                search_fields=['programme__code__icontains'],
                ),
            help_text = "Tapez le code de la formation ou 2 espaces pour avoir la liste complète. Sélection multiple possible.",
            )
    activite_type_list = forms.MultipleChoiceField(
            choices=TYPES_ACT_EXAM,
            label=u"Types d'preuves",
            widget = Select2MultipleWidget
            )

    date_debut = forms.DateField(input_formats = settings.DATE_INPUT_FORMATS, widget=DatePickerInput(format='%d/%m/%Y')) # 
    date_fin = forms.DateField(input_formats = settings.DATE_INPUT_FORMATS, widget=DatePickerInput(format='%d/%m/%Y')) # 
    
    def __init__(self, *args, **kwargs):
        super(ExamenSelectForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Submit('submit','Envoyer les convocations',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))

        self.helper.form_method='POST'


class AffichageExamenSelectForm(forms.Form):
    formation = forms.ModelChoiceField(
            queryset=Formation.objects.filter(annee_univ__encours=True).order_by('programme__ordre'),
            label=u"Formation concernée par l'affichage des convocations",
            widget=ModelSelect2Widget(
                model=Formation,
                search_fields=['programme__code__icontains'],
                ),
            help_text = "Tapez le code de la formation ou 2 espaces pour avoir la liste complète.",
            )
    activite_type_list = forms.MultipleChoiceField(
            choices=TYPES_ACT_EXAM,
            label=u"Types d'preuves",
            widget = Select2MultipleWidget
            )

    date_debut = forms.DateField(input_formats = settings.DATE_INPUT_FORMATS, widget=DatePickerInput(format='%d/%m/%Y')) # 
    date_fin = forms.DateField(input_formats = settings.DATE_INPUT_FORMATS, widget=DatePickerInput(format='%d/%m/%Y')) # 
    
    def __init__(self, *args, **kwargs):
        super(AffichageExamenSelectForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Submit('submit','Générer la répartition',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))

        self.helper.form_method='POST'


class SeanceSelectionForm(forms.Form):
    enseignant = forms.ModelChoiceField(
            queryset=Enseignant.objects.filter(situation='A').order_by('nom', 'prenom'),
            label=u"Enseignant",
            widget=ModelSelect2Widget(
                model=Enseignant,
                search_fields=['nom__icontains','prenom__icontains'],
                ),
            help_text = "Tapez le nom ou prénom ou 2 espaces pour avoir la liste complète",
            )
    periode = forms.ChoiceField(
            choices=Periode.objects.values_list('id', 'code'),
            label=u"Semestre",
            widget = Select2Widget
            )
    activite = forms.ModelChoiceField(
            queryset=Activite.objects.filter(module__formation__annee_univ__encours=True).order_by('module__formation__programme__ordre', 'module__matiere__code'),
            label=u"Activité",
            widget=ModelSelect2Widget(
                    model=Activite,
                    search_fields=['module__matiere__code__icontains',],
                    dependent_fields={'enseignant':'assuree_par', 'periode':'module__periode__periode'},
                ),
        )
    date = forms.DateField(input_formats = settings.DATE_INPUT_FORMATS, widget=DatePickerInput(format='%d/%m/%Y'), initial=datetime.date.today()) # 
    
    def __init__(self, *args, **kwargs):
        super(SeanceSelectionForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Submit('submit','Ajouter',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))

        self.helper.form_method='POST'



class SeanceEtudiantSelectionForm(forms.Form):
    formation = forms.ModelChoiceField(
            queryset=Formation.objects.filter(annee_univ__encours=True).order_by('programme__ordre'),
            label=u"Formation",
            widget=ModelSelect2Widget(
                model=Formation,
                search_fields=['programme__code__icontains'],
                ),
            help_text = "Tapez le code de la formation (1CP, 2CP, 1CS, 2ST, 2SL...) ou 2 espaces pour avoir la liste complète",
            )
    periode = forms.ChoiceField(
            choices=Periode.objects.values_list('id', 'code'),
            label=u"Semestre",
            widget = Select2Widget
            )
    type_activite = forms.ChoiceField(
            choices= TYPES_ACT,
            label=u"Type",
            widget = Select2Widget
            ) 
    activite = forms.ModelChoiceField(
            queryset=Activite.objects.filter(module__formation__annee_univ__encours=True).order_by('module__formation__programme__ordre', 'module__matiere__code'),
            label=u"Activité",
            widget=ModelSelect2Widget(
                    model=Activite,
                    search_fields=['module__matiere__code__icontains',],
                    dependent_fields={'formation':'cible__activites__module__formation', 'periode':'module__periode__periode', 'type_activite':'type'},
                ),
        )
    date = forms.DateField(input_formats = settings.DATE_INPUT_FORMATS, widget=DatePickerInput(format='%d/%m/%Y'), initial=datetime.date.today()) # 
    
    inscription_absent_list =  forms.ModelMultipleChoiceField(
            queryset=Inscription.objects.filter(decision_jury='C', formation__annee_univ__encours=True).order_by('etudiant__nom', 'etudiant__prenom'),
            label=u"Liste des absents",
            widget=ModelSelect2MultipleWidget(
                    model=Inscription,
                    search_fields=['etudiant__nom__icontains', 'etudiant__prenom__icontains',],
                    dependent_fields={'formation':'formation','periode':'inscription_periodes__periodepgm__periode', 'activite':'inscription_periodes__groupe__activites'},
                ),
            help_text = "Tapez les noms des absents. Tapez le nom ou prénom ou 2 espaces pour avoir la liste complète.",
            required = True
        )
    def __init__(self, *args, **kwargs):
        super(SeanceEtudiantSelectionForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Submit('submit','Signaler',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))

        self.helper.form_method='POST'


class ReleveNotesUpdateForm(forms.Form):

    def __init__(self, inscription_pk, *args, **kwargs):
        super(ReleveNotesUpdateForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        inscription_=Inscription.objects.get(id=inscription_pk)
        for periode_ in inscription_.inscription_periodes.all():
            self.fields[periode_.periodepgm.code]=forms.DecimalField(initial=periode_.moy, max_digits=4, decimal_places=2)
            for ue_ in periode_.resultat_ues.all():
                for resultat_ in ue_.resultat_matieres.all():
                    self.fields[resultat_.module.matiere.code]=forms.DecimalField(widget=forms.NumberInput(attrs={'onchange':'recalculer()'}), initial=resultat_.moy_post_delib, max_digits=4, decimal_places=2, required=False)
        self.fields['proposition_decision_jury']=forms.ChoiceField(choices = DECISIONS_JURY, required=False, initial=inscription_.proposition_decision_jury)
        self.fields['moyenne']=forms.DecimalField(max_digits=4, decimal_places=2, required=False, initial=inscription_.moyenne_post_delib())
        self.helper.form_method='POST'


class InscriptionUpdateForm(forms.Form):
    DECISIONS_JURY=(
        ('C','Inscrit'),
        ('R','Redouble'),
        ('N','Non Admis'),
        ('F','Abandon'),
        ('FT','Transfert'),
        ('AJ','Ajournement'),
        ('P','Prolongation'),
        ('M1', 'Raisons médicales'),
        ('M2', 'Raisons personnelles'),
        ('M3', 'Raisons personnelles (Covid 19)'),
        ('M4', 'Raisons familiales'),
        ('X', 'Non Inscrit'),
    )

    def __init__(self, inscription_pk, *args, **kwargs):
        super(InscriptionUpdateForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        inscription_=Inscription.objects.get(id=inscription_pk)
        # créer inscription_periodes selon le programme
        for periode_ in inscription_.formation.programme.periodes.all():
            InscriptionPeriode.objects.get_or_create(inscription=inscription_, periodepgm=periode_, defaults={
                    'inscription':inscription_,
                    'periodepgm':periode_,
                })
        
        for periode_ in inscription_.inscription_periodes.all():
            self.fields['groupe_'+str(periode_.id)]=forms.ModelChoiceField(
                initial=periode_.groupe,
                required=True,
                queryset=Groupe.objects.filter(section__formation=inscription_.formation).order_by('code'),
                label=u"Groupe du "+periode_.periodepgm.periode.code
            )
        self.fields['decision_jury']=forms.ChoiceField(choices = self.DECISIONS_JURY, required=False, initial=inscription_.decision_jury)
        self.helper.add_input(Submit('submit','Modifier',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.helper.form_method='POST'

class NotesUpdateForm(forms.Form):
    def __init__(self, groupe_pk, module_pk, request, *args, **kwargs):
        super(NotesUpdateForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        try:
            module_=get_object_or_404(Module, id = module_pk)
            groupe_=get_object_or_404(Groupe, id = groupe_pk)
            liste_inscrits=Inscription.objects.filter(inscription_periodes__groupe=groupe_.id, inscription_periodes__periodepgm=module_.periode).order_by('etudiant__nom', 'etudiant__prenom')
            #liste_inscrits=Inscription.objects.filter(groupe=groupe_pk)
            liste_evaluations=Evaluation.objects.filter(module=module_pk)
            if module_.somme_ponderation() != 1 and module_.somme_ponderation() != 0:
                messages.error(request, "ATTENTION! La somme des pondérations des évaluations n'est pas égale à 1. Le coordinateur(trice) devrait corriger la formule")
                
            for inscrit_ in liste_inscrits:
                self.fields[inscrit_.etudiant.matricule]=forms.CharField(initial=str(inscrit_.etudiant), disabled = True)
                resultat_=get_object_or_404(Resultat, inscription=inscrit_, module = module_pk)
                for eval_ in liste_evaluations :
                    note_, created=Note.objects.get_or_create(resultat=resultat_, evaluation=eval_, defaults = {'resultat':resultat_,'evaluation':eval_, 'note':0})
                    self.fields[str(inscrit_.etudiant.matricule)+"_"+str(eval_.id)]=forms.DecimalField(initial=note_.note, label='',
                                        widget=forms.NumberInput(attrs={'onchange':'update_moy("'+inscrit_.etudiant.matricule+'")'}),
                                        max_digits=4, 
                                        decimal_places=2, 
                                        required = False,
                                        )
                    if (resultat_.acquis or resultat_.inscription.decision_jury!='C') and (not request.user.is_direction()):
                        self.fields[str(inscrit_.etudiant.matricule)+"_"+str(eval_.id)].widget.attrs['readonly']=True
                self.fields[inscrit_.etudiant.matricule+'_moy']=forms.DecimalField(initial=resultat_.moy, label='', 
                                                                                   max_digits=4, 
                                                                                   decimal_places=2,
                                                                                   required = False)
                if (liste_evaluations.exists() or resultat_.acquis or resultat_.inscription.decision_jury!='C') and( not request.user.is_direction()) :
                    self.fields[inscrit_.etudiant.matricule+'_moy'].widget.attrs['readonly']=True
                    

            self.fields[str(groupe_.id)+'_'+str(module_.id)]=forms.BooleanField(initial=False, label='Version Finale :', help_text='Saisie de toutes les notes de ce groupe est terminée', required = False)
            self.fields['otp']=forms.CharField(required=True, label="Mot de Passe (Envoyé par SMS)", help_text="Saisir ici le mot de passe qu'on vient de vous envoyer par SMS. Si vous ne le recevez pas dans la minute qui suit, merci de vérifier que le numéro de téléphone associé à votre compte est correct.")
            self.helper.add_input(Submit('submit','Modifier',css_class='btn-primary'))
            self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
            self.helper.form_method='POST'
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(request, "ERREUR: lors de la construction du formaulaire de saisie des notes. Merci de le signaler à l'administrateur.")

#TODO sortir du code et mettre dans la base sous forme de table
COMPETENCE_EVAL={
    'Jury':(('0.90', 'A: Très bien'), ('0.75','B: Bien'), ('0.65','C: Assez bien'), ('0.50', 'D: Passable'), ('0.40', 'E: Médiocre'), ('0.25', 'F: Mauvais'), ('0.00', 'Choisir')),
    'Rapporteur': (('0.90', 'A: Très bien'), ('0.75','B: Bien'), ('0.65','C: Assez bien'), ('0.50', 'D: Passable'), ('0.40', 'E: Médiocre'), ('0.25', 'F: Mauvais'), ('0.00', 'Choisir')),
    'Encadreur':(('0.80', 'A: Très bien'), ('0.75','B: Bien'), ('0.65','C: Assez bien'), ('0.50', 'D: Passable'), ('0.40', 'E: Médiocre'), ('0.25', 'F: Mauvais'), ('0.00', 'Choisir')),
    'Rapport':(('0.90', 'A: Très bien'), ('0.75','B: Bien'), ('0.65','C: Assez bien'), ('0.50', 'D: Passable'), ('0.40', 'E: Médiocre'), ('0.25', 'F: Mauvais'), ('0.00', 'Choisir')),
    'Soutenance':(('0.90', 'A: Très bien'), ('0.75','B: Bien'), ('0.65','C: Assez bien'), ('0.50', 'D: Passable'), ('0.40', 'E: Médiocre'), ('0.25', 'F: Mauvais'), ('0.00', 'Choisir')),
    'Poster':(('0.90', 'A: Très bien'), ('0.75','B: Bien'), ('0.65','C: Assez bien'), ('0.50', 'D: Passable'), ('0.40', 'E: Médiocre'), ('0.25', 'F: Mauvais'), ('0.00', 'Choisir')),

}
class NotesPFEUpdateForm(forms.Form):
    def __init__(self, groupe_pk, module_pk, request, *args, **kwargs):
        super(NotesPFEUpdateForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        try:
            module_=get_object_or_404(Module, id = module_pk)
            groupe_=get_object_or_404(Groupe, id = groupe_pk)
            liste_inscrits=Inscription.objects.filter(inscription_periodes__groupe=groupe_pk, inscription_periodes__periodepgm__periode=module_.periode.periode)
            liste_evaluations=Evaluation.objects.filter(module=module_pk)
            soutenance_, created = Soutenance.objects.get_or_create(groupe=groupe_, defaults={
                    'groupe':groupe_,
                })
            pfe_, created = PFE.objects.get_or_create(groupe=groupe_, defaults={
                    'groupe':groupe_,
                })
            for inscrit_ in liste_inscrits:
                resultat_=get_object_or_404(Resultat, inscription=inscrit_, module__matiere = module_.matiere)
                for eval_ in liste_evaluations :
                    note_, created=Note.objects.get_or_create(resultat=resultat_, evaluation=eval_, defaults = {
                        'resultat':resultat_,
                        'evaluation':eval_,
                        'note':0
                        })
                    for competence_ in eval_.competence_elements.all():
                        note_competence_element, created= NoteCompetenceElement.objects.get_or_create(evaluation_competence_element=competence_, note_globale=note_, defaults={
                                'evaluation_competence_element':competence_, 
                                'note_globale':note_,
                                'valeur':0,
                            })
                        if competence_.commune_au_groupe:
                            key_=str(groupe_.code)+"_"+str(eval_.id)+'_'+competence_.competence_element.code
                            if not key_ in self.fields.keys(): 
                                self.fields[key_]=forms.ChoiceField(choices=COMPETENCE_EVAL[eval_.type], required = True, label='', initial=str(round(decimal.Decimal(note_competence_element.valeur),2)), widget=forms.Select(attrs={'onchange':"update_"+eval_.type+'()'}))
                        else:
                            key_=str(inscrit_.etudiant.matricule)+"_"+str(eval_.id)+'_'+competence_.competence_element.code
                            self.fields[key_]=forms.ChoiceField(choices=COMPETENCE_EVAL[eval_.type], required = True, label=str(inscrit_.etudiant), initial=str(round(decimal.Decimal(note_competence_element.valeur),2)), widget=forms.Select(attrs={'onchange':"update_"+eval_.type+'()'}))
                    self.fields[str(inscrit_.etudiant.matricule)+"_"+str(eval_.id)]=forms.DecimalField(label='', initial=note_.note, max_digits=4, decimal_places=2, disabled=False)
                    if not (request.user.is_direction() or request.user.is_stage()):
                        self.fields[str(inscrit_.etudiant.matricule)+"_"+str(eval_.id)].widget.attrs['readonly'] = True
                    else:
                        self.fields[str(inscrit_.etudiant.matricule)+"_"+str(eval_.id)].widget.attrs['onchange'] = "update_moyenne()"
                self.fields[inscrit_.etudiant.matricule+'_moy']=forms.DecimalField(label='', initial=resultat_.moy, max_digits=4, decimal_places=2, disabled = False)
                self.fields[inscrit_.etudiant.matricule+'_moy'].widget.attrs['readonly'] = True
                self.fields[inscrit_.etudiant.matricule+'_mention']=forms.ChoiceField(choices=MENTION, label='', initial=inscrit_.mention, disabled = False)
                self.fields[inscrit_.etudiant.matricule+'_mention'].widget.attrs['readonly'] = True
            if request.user.is_stage():
                required_=True
            else:
                required_=False
            self.fields[str(pfe_.id)+'_intitule']=forms.CharField(required=False, disabled=not required_, initial=pfe_.intitule, label="")
            self.fields[str(pfe_.id)+'_promoteur']=forms.CharField(required=False, disabled= not required_, label="", initial=pfe_.promoteur)
            
            enseignant_nb_encadrements_list=[] 
            for enseignant_ in Enseignant.objects.all().order_by('nom','prenom'):
                enseignant_nb_encadrements_list.append((enseignant_.id, str(enseignant_)+" Encadrements("+str(enseignant_.nb_encadrements())+")"))
            coencadrants_initial=[]
            for enseignant_ in pfe_.coencadrants.all().order_by('nom','prenom'):
                coencadrants_initial.append((enseignant_.id, str(enseignant_)+" Encadrements("+str(enseignant_.nb_encadrements())+")"))

            self.fields[str(pfe_.id)+'_coencadrants'] = forms.MultipleChoiceField(
                label="",
                choices=enseignant_nb_encadrements_list,
                initial=[enseignant_.id for enseignant_ in pfe_.coencadrants.all()],
                widget=Select2MultipleWidget,
                help_text = "Vous pouvez séléctionner plusieurs enseignants. Tapez un nom ou prénom ou 2 espaces pour avoir la liste complète.",
                required = False,
                disabled=not required_,
            )
#             self.fields[str(pfe_.id)+'_coencadrants'] = forms.ModelMultipleChoiceField(
#                     queryset=Enseignant.objects.all().order_by('nom', 'prenom'),
#                     initial=pfe_.coencadrants.all(),
#                     label="",
#                     widget=ModelSelect2MultipleWidget(
#                             model=Enseignant,
#                             search_fields=['nom__icontains','prenom__icontains'],
#                         ),
#                     help_text = "Sélection multiple possible. Tapez le nom ou prénom de l'enseignant ou deux espaces pour avoir la liste complète.",
#                     required = False,
#                     disabled=not required_,
#                 )
            self.fields[str(soutenance_.id)+'_coencadrant']=forms.ModelChoiceField(
                label="Coencadrant", 
                queryset=pfe_.coencadrants.all().order_by('nom','prenom'),
                initial=soutenance_.coencadrant,            
                required = False,
                disabled=not required_,
                )
                
            self.fields[str(soutenance_.id)+'_president']=forms.ModelChoiceField(required=False, disabled=not required_, label="Président", queryset=Enseignant.objects.all().order_by('nom','prenom'), initial=soutenance_.president)
            self.fields[str(soutenance_.id)+'_rapporteur']=forms.ModelChoiceField(required=False, disabled=not required_, label="Rapporteur", queryset=Enseignant.objects.all().order_by('nom','prenom'), initial=soutenance_.rapporteur)
            self.fields[str(soutenance_.id)+'_examinateur']=forms.ModelChoiceField(required=False, disabled=not required_, label="Examinateur", queryset=Enseignant.objects.all().order_by('nom','prenom'), initial=soutenance_.examinateur)
            self.fields[str(soutenance_.id)+'_assesseur1']=forms.ModelChoiceField(required=False, disabled=not required_, label="Assesseur1", queryset=Enseignant.objects.all().order_by('nom','prenom'), initial=soutenance_.assesseur1)
            self.fields[str(soutenance_.id)+'_assesseur2']=forms.ModelChoiceField(required=False, disabled=not required_, label="Assesseur2", queryset=Enseignant.objects.all().order_by('nom','prenom'), initial=soutenance_.assesseur2)
            self.fields[str(soutenance_.id)+'_invite1']=forms.CharField(required=False, disabled=not required_, label="Invité", initial=soutenance_.invite1)
            self.fields[str(soutenance_.id)+'_invite2']=forms.CharField(required=False, disabled=not required_, label="Invité", initial=soutenance_.invite1)
            self.fields[str(soutenance_.id)+'_date']=forms.DateField(required=False, disabled=not required_, label='', input_formats = settings.DATE_INPUT_FORMATS, widget=DatePickerInput(format='%d/%m/%Y'), initial=soutenance_.date)
            self.fields[str(soutenance_.id)+'_depot_biblio']=forms.ChoiceField(required=False, choices=OPTIONS_DEPOT,
                                                                               widget=forms.RadioSelect(attrs={'class': 'form-check-inline'}), 
                                                                               initial=soutenance_.depot_biblio, label="Le jury autorise le dépôt du mémoire à la bibliothèque")
            self.fields[str(groupe_.id)+'_'+str(module_.id)]=forms.BooleanField(disabled=not required_, initial=False, label='Version Finale/Etablir PV :', help_text='Saisie de toutes les notes de ce PFE est terminée et sera archivée', required = False)
            self.helper.add_input(Submit('submit','Modifier',css_class='btn-primary'))
            self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
            self.helper.form_method='POST'
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request, "ERREUR: lors de la construction du formulaire d'évaluation d'un PFE. Merci de le signaler à l'administrateur")

class OrganismeForm(forms.ModelForm):
    class Meta:
        model = Organisme
        fields = ['sigle', 'nom', 'adresse', 'pays', 'type', 'statut', 'nature', 'secteur', 'taille']

    def __init__(self, *args, **kwargs):
        super(OrganismeForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.fields['sigle'].help_text="Saisir en Majuscule."
        self.helper.add_input(Submit('submit','Créer',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.helper.form_method='POST'

class PictureWidget(forms.widgets.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        html = Template("""<img src="$media$link" width=100% />""")
        return mark_safe(html.substitute(media=settings.MEDIA_URL, link=value))

class InstitutionDetailForm(forms.ModelForm):
    class Meta:
        model = Institution
        fields = ['nom','nom_a', 'sigle', 'adresse', 'ville', 'tel','fax', 'web', 'illustration_cursus', 'banniere', 'logo', 'logo_bis','header', 'footer']
    def __init__(self, *args, **kwargs):
        super(InstitutionDetailForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.fields['banniere']=forms.ImageField(label='Bannière', required=False, widget=PictureWidget)
        self.fields['illustration_cursus']=forms.ImageField(label='Illustration du cursus', required=False, widget=PictureWidget)
        self.fields['logo']=forms.ImageField(label='Logo', required=False, widget=PictureWidget)
        self.fields['logo_bis']=forms.ImageField(label='Logo', required=False, widget=PictureWidget)
        self.fields['header']=forms.ImageField(label='Entête', required=False, widget=PictureWidget)
        self.fields['footer']=forms.ImageField(label='Peid de page', required=False, widget=PictureWidget)
        for key_ in self.fields.keys():
            self.fields[key_].widget.attrs['readonly']=True


class PFEDetailForm(forms.ModelForm):
    class Meta:
        model = PFE
        exclude = ['groupe']

    def __init__(self, *args, **kwargs):
        super(PFEDetailForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.fields['specialites']=forms.ModelMultipleChoiceField(
            queryset = Specialite.objects.all(),
            widget=ModelSelect2MultipleWidget(
                model=Specialite,
            ),
        )
        self.fields['coencadrants']=forms.ModelMultipleChoiceField(
            queryset = Enseignant.objects.all(),
            widget=ModelSelect2MultipleWidget(
                model=Enseignant,
            ),
        )
        self.fields['reserve_pour']=forms.ModelMultipleChoiceField(
            queryset = Inscription.objects.all(),
            widget=ModelSelect2MultipleWidget(
                model=Inscription,
            ),
        )

        for key_ in self.fields.keys():
            self.fields[key_].widget.attrs['readonly']=True

class EnseignantDetailForm(forms.ModelForm):
    class Meta:
        model = Enseignant
        exclude = ['user', 'edt', 'otp', 'charge_statut']

    def __init__(self, *args, **kwargs):
        super(EnseignantDetailForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Button('cancel', 'Retour', css_class='btn-secondary', onclick="window.history.back()"))

        for key_ in self.fields.keys():
            self.fields[key_].widget.attrs['readonly']=True

class SelectOrCreateOrganismeForm(forms.Form):
    organisme= forms.ModelChoiceField(
            queryset=Organisme.objects.all().order_by('sigle', 'nom'),
            label="Organisme",
            widget=ModelSelect2Widget(
                    model=Organisme,
                    search_fields=['sigle__icontains', 'nom__icontains']
                ),
            help_text = "Tapez le sigle ou nom de l'organisme. S'il n'apparaît pas, merci de cliquer sur le bouton Nouveau",
            required = True
        )

    def __init__(self, *args, **kwargs):
        super(SelectOrCreateOrganismeForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Submit('submit','Sélectionner',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Nouveau', css_class='btn-secondary', onclick="window.location.href='"+reverse('organisme_create_for_pfe_create')+"'"))
        self.helper.form_method='POST'


class SelectSingleModuleForm(forms.Form):

    module= forms.ModelChoiceField(
            queryset=Module.objects.all().order_by('formation__annee_univ__annee_univ','formation__programme__ordre','periode__periode__ordre','matiere__code'),
            label=u"Module",
            widget=ModelSelect2Widget(
                    model=Module,
                    search_fields=['matiere__code__icontains','matiere__titre__icontains'],

                ),
            help_text = "Tapez le code matière ou un mot dans l'intitulé de la matière",
            required = True
        )
    
    def __init__(self, *args, **kwargs):
        super(SelectSingleModuleForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Submit('submit','Copier',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.helper.form_method='POST'

class SelectModuleForm(forms.Form):
    
    def __init__(self, formation_pk, *args, **kwargs):
        super(SelectModuleForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        formation_=Formation.objects.get(id=formation_pk)
        for periode_ in formation_.programme.periodes.all():
            module_list=Module.objects.filter(formation=formation_, periode=periode_)
            for module_ in module_list:
                self.fields['calcul_ne_'+str(module_.id)]=forms.DecimalField(
                    initial=module_.calcul_note_eliminatoire(),
                    label="",
                    max_digits=4, decimal_places=2,
                    required = True
                    )


                self.fields['select_module_'+str(module_.id)]=forms.BooleanField(
                    initial=False,
                    label="",
                    required=False
                    )
        self.helper.form_method='POST'


class SelectPVSettingsForm(forms.Form):
    
    def __init__(self, formation_pk, *args, **kwargs):
        super(SelectPVSettingsForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        formation_=Formation.objects.get(id=formation_pk)
        for periode_ in formation_.programme.periodes.all():
            matiere_list=[]
            for ue in periode_.ues.all():
                for matiere in ue.matieres.all():
                    if not (matiere.code, matiere.code) in matiere_list:
                        matiere_list.append((matiere.code, matiere.code))
            self.fields['matieres_affichage_'+periode_.periode.code]=forms.MultipleChoiceField(required=False, 
                                                                 label='Matières du '+periode_.periode.code+' à afficher sur le PV',
                                                                 widget=forms.CheckboxSelectMultiple,
                                                                 choices=matiere_list,
                                                                 help_text="Sélectionner les modules du semestre "+periode_.periode.code+" à afficher sur le PV.")
            self.fields['matieres_moyenne_'+periode_.periode.code]=forms.MultipleChoiceField(required=False, 
                                                                 label='Matières du '+periode_.periode.code+' à considérer dans le calcul de la moyenne',
                                                                 widget=forms.CheckboxSelectMultiple,
                                                                 choices=matiere_list,
                                                                 help_text="Sélectionner les modules du semestre "+periode_.periode.code+" à considérer dans le calcul de la moyenne.")
        self.fields['photo'] = forms.BooleanField(required=False, initial=False, help_text="Cochez pour faire apparaître les photos sur le PV.",
                                                                label='Photo')
        self.fields['sort'] = forms.BooleanField(required=False, initial=True, help_text="Cochez pour faire un tri par rang du PV.",
                                                                label='Tri par rang')
        self.fields['anonyme'] = forms.BooleanField(required=False, initial=False, help_text="Cochez pour rendre le PV anonyme.",
                                                                label='Anonyme')
        self.fields['ne'] = forms.BooleanField(required=False, initial=False, help_text="Cochez pour afficher le nombre de notes éliminatoires",
                                                                label='Notes éliminatoires')
        self.fields['rang'] = forms.BooleanField(required=False, initial=False, help_text="Cochez pour afficher le rang.",
                                                                label='Rang')
        self.fields['signatures'] = forms.BooleanField(required=False, initial=False, help_text="Cochez pour prévoir un espace de signatures en pied de page.",
                                                                label='Signatures')

        self.helper.form_method='POST'
        
class SelectPVAnnuelSettingsForm(forms.Form):
    photo = forms.BooleanField(required=False, initial=True, help_text="Cochez pour faire apparaître les photos sur le PV.",
                                                                label='Photo')
    sort = forms.BooleanField(required=False, initial=True, help_text="Cochez pour faire un tri par rang du PV.",
                                                                label='Tri par rang')
    anonyme = forms.BooleanField(required=False, initial=False, help_text="Cochez pour rendre le PV anonyme.",
                                                                label='Anonyme')
    ne = forms.BooleanField(required=False, initial=True, help_text="Cochez pour afficher le nombre de notes éliminatoires",
                                                                label='Notes éliminatoires')
    moy_ue = forms.BooleanField(required=False, initial=False, help_text="Cochez pour afficher la moyenne par UE",
                                                                label='Moyenne UE')
    rang = forms.BooleanField(required=False, initial=True, help_text="Cochez pour afficher le rang.",
                                                                label='Rang')
    signatures = forms.BooleanField(required=False, initial=True, help_text="Cochez pour prévoir un espace de signatures en pied de page.",
                                                                label='Signatures')

    rachat = forms.BooleanField(required=False, initial=False, help_text="Cochez pour rajouter la fonction de rachat.",
                                                                label='Rachat')

    reserve = forms.BooleanField(required=False, initial=False, help_text="Cochez pour rendre le PV réservé à l'administration.",
                                                                label='Réservé')

    xls = forms.BooleanField(required=False, initial=False, help_text="Cochez pour recevoir le PV au format Excel.",
                                                                label='Excel')

    
    def __init__(self, *args, **kwargs):
        super(SelectPVAnnuelSettingsForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Submit('submit','Générer',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))

        self.helper.form_method='POST'
        

class FeedbackUpdateForm(forms.Form):
    REPONSE=(
        ('++','++'),
        ('+','+'),
        ('-','-'),
        ('--','--'),
    )

    def __init__(self, inscription_pk, periode_pk, *args, **kwargs):
        super(FeedbackUpdateForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        try:
            inscription_=Inscription.objects.get(id=inscription_pk)
            periodepgm_=PeriodeProgramme.objects.get(id=periode_pk)
            inscription_periode_=InscriptionPeriode.objects.get(inscription=inscription_, periodepgm=periode_pk)
            groupe_section=inscription_periode_.groupe.section.groupes.all().filter(code__isnull=True).get() # le groupe qui représente la section
            activites_suivies_list=Activite.objects.filter(cible__in=[inscription_periode_.groupe, groupe_section], module__periode__periode=periodepgm_.periode)
            module_traite_list=[]
            for activite_suivie in activites_suivies_list:
                if not activite_suivie.module.id in module_traite_list:
                    module_traite_list.append(activite_suivie.module.id)
                    key_=str(activite_suivie.module.id)
                    feedback_, created=Feedback.objects.get_or_create(module=activite_suivie.module, inscription=inscription_, defaults={
                        'module':activite_suivie.module,
                        'inscription':inscription_,
                        'show':False
                    })
                    self.fields[key_]=forms.CharField(max_length=1000, required=False, widget=forms.Textarea, label='Commentaire facultatif', initial=feedback_.comment)
                    
                    if activite_suivie.module.matiere.mode_projet:
                        question_list=Question.objects.exclude(projet_na=True).order_by('code')
                    else:
                        question_list=Question.objects.exclude(cours_na=True).order_by('code')
                    for question_ in question_list:
                        key_=str(activite_suivie.module.id)+'_'+str(question_.code)
                        reponse_, created=Reponse.objects.get_or_create(feedback=feedback_, question=question_, defaults={
                            'feedback':feedback_,
                            'question':question_
                        })
                        
                        self.fields[key_]=forms.ChoiceField(choices=self.REPONSE, required=True, label='', initial=reponse_.reponse,
                                 widget=forms.RadioSelect(
                                    attrs={
                                    #'class': 'custom-control custom-radio custom-control-inline'
                                    'class': 'form-check-inline'
                                    }
                                ) 
                        )
                
            self.helper.form_method='POST'
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request, "ERREUR: lors de la construction du formulaire de saisie des feedbacks. Merci de le signaler à l'administrateur")

class AbsencesForm(forms.Form):
    
    def __init__(self, groupe_pk, module_pk, *args, **kwargs):
        super(AbsencesForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.fields['seance_date']=forms.DateField(required=True, label="Date de la séance", input_formats = settings.DATE_INPUT_FORMATS, widget=DatePickerInput(format='%d/%m/%Y'), initial=datetime.date.today()) #
        self.fields['seance_rattrapage']=forms.BooleanField(initial=False, required=False, label="Séance de rattrapage?")
        module_=get_object_or_404(Module, id=module_pk)
        resultat_list=Resultat.objects.filter(acquis=False, module__matiere=module_.matiere, resultat_ue__inscription_periode__groupe=groupe_pk, inscription__decision_jury='C').order_by('inscription__etudiant__nom')
        choice_list=[]
        for resultat_ in resultat_list:
            choice_list.append(
                (resultat_.inscription.etudiant.matricule, resultat_.inscription.etudiant)
                ) 
        self.fields['absence_list']=forms.MultipleChoiceField(required=False, choices=choice_list, label="Cochez les absents",
                                        widget=forms.CheckboxSelectMultiple())
        self.helper.add_input(Submit('submit','Signaler',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.helper.form_method='POST'

class ImportNotesForm(forms.Form):
    formation=forms.ModelChoiceField(queryset=Formation.objects.filter().order_by('-annee_univ__annee_univ','programme__ordre'))
    file=forms.FileField(label='Choisir un fichier', widget=forms.FileInput(attrs={'class':"custom-file-input"}))
    
    def __init__(self, *args, **kwargs):
        super(ImportNotesForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Submit('submit','Importer',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.helper.form_method='POST'


class ImportFeedbackForm(forms.Form):
    module=forms.ModelChoiceField(queryset=Module.objects.all())
    file=forms.FileField(label='Choisir un fichier', widget=forms.FileInput(attrs={'class':"custom-file-input"}))
    
    def __init__(self, module_pk, *args, **kwargs):
        super(ImportFeedbackForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.fields['module']=forms.ModelChoiceField(queryset=Module.objects.filter(id=module_pk), initial=0)
        self.helper.layout=Layout(
            Div(
                'module', Field('file'), css_class="row"
            ),
            FormActions(
                Submit('submit','Importer'),
                HTML('<a class="btn btn-secondary" href="{% url "module_list" %}">Annuler</a>')
            )
        )
        self.helper.form_method='POST'

class PlanificationImportFileForm(forms.Form):
    periode = forms.ModelChoiceField(queryset=Periode.objects.all(), label='Choisir Semestre')
    file=forms.FileField(label='Choisir un fichier', widget=forms.FileInput(attrs={'class':"custom-file-input"}))
    
    def __init__(self, *args, **kwargs):
        super(PlanificationImportFileForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Submit('submit','Importer',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.helper.form_method='POST'

class EDTSelectForm(forms.Form):
    code = forms.CharField(max_length=256, label="Code d'autorisation")
    date_debut = forms.DateTimeField(input_formats = settings.DATE_INPUT_FORMATS, widget=DateTimePickerInput(format='%d/%m/%Y'), initial=datetime.date.today())
    date_fin = forms.DateTimeField(input_formats = settings.DATE_INPUT_FORMATS, widget=DateTimePickerInput(format='%d/%m/%Y'), initial=datetime.date.today() + datetime.timedelta(days = 7))
    google_calendar_list = forms.ModelMultipleChoiceField(
            queryset=GoogleCalendar.objects.all().order_by('code'),
            label=u"Liste des agendas",
            widget=ModelSelect2MultipleWidget(
                    model=GoogleCalendar,
                    search_fields=['code__icontains'],
                ),
            help_text = "Sélection multiple possible. Tapez le nom du groupe ou deux espaces pour avoir la liste complète.",
            required = True
        )
    
    def __init__(self, *args, **kwargs):
        super(EDTSelectForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Submit('submit','Effacer',css_class='btn-danger'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.helper.form_method='POST'

class EDTImportFileForm(forms.Form):
    code = forms.CharField(max_length=256, label="Code d'autorisation")
    date_debut = forms.DateTimeField(input_formats = settings.DATE_INPUT_FORMATS, widget=DateTimePickerInput(format='%d/%m/%Y'), initial=datetime.date.today())
    date_fin = forms.DateTimeField(input_formats = settings.DATE_INPUT_FORMATS, widget=DateTimePickerInput(format='%d/%m/%Y'), initial=datetime.date.today() + datetime.timedelta(days = 7))
    file=forms.FileField(label='Choisir un fichier', widget=forms.FileInput(attrs={'class':"custom-file-input"}))
    
    def __init__(self, *args, **kwargs):
        super(EDTImportFileForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Submit('submit','Importer',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.helper.form_method='POST'

class ImportFileForm(forms.Form):
    file=forms.FileField(label='Choisir un fichier', widget=forms.FileInput(attrs={'class':"custom-file-input"}))
    
    def __init__(self, *args, **kwargs):
        super(ImportFileForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Submit('submit','Importer',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.helper.form_method='POST'


class OTPImportFileForm(forms.Form):
    file=forms.FileField(label='Choisir un fichier', widget=forms.FileInput(attrs={'class':"custom-file-input"}))
    #file=forms.FileField(label='Choisir un fichier')
    otp=forms.CharField(required=True, label="Mot de Passe (Envoyé par SMS)", help_text="Saisir ici le mot de passe qu'on vient de vous envoyer par SMS. Si vous ne le recevez pas dans la minute qui suit, merci de vérifier que le numéro de téléphone associé à votre compte est correct.")
    
    def __init__(self, *args, **kwargs):
        super(OTPImportFileForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Submit('submit','Importer',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.helper.form_method='POST'



class ImportAffectationDiplomeForm(forms.Form):

    diplome = forms.ChoiceField(
            choices=Diplome.objects.values_list('id','intitule'),
            label=u"Diplome",
            widget = Select2Widget(
            #attrs={'style':'width:800px; height:10px;'}
            ),
            required = True,
            help_text = "Choisir le diplome",
            )
    formation = forms.ModelChoiceField(
            queryset=Formation.objects.filter(programme__ordre__gte=5).order_by('-annee_univ__annee_univ'),
            label=u"Formation",
            widget=ModelSelect2Widget(
                    model=Formation,
                    search_fields=['programme__code__icontains',],
                    dependent_fields={'diplome':'programme__diplome'},
                    #attrs={'style':'width:800px; height:10px;'}
                ),
            help_text = "Choisir la formation. Tapez deux espaces pour avoir toute la liste.",
            required = True
        )
    config_charge = forms.ModelChoiceField(
        queryset=ActiviteChargeConfig.objects.all().order_by('type'), required=True, label="Type de l'activité")
    file=forms.FileField(label='Choisir un fichier', widget=forms.FileInput(attrs={'class':"custom-file-input"}))
    
    def __init__(self, *args, **kwargs):
        super(ImportAffectationDiplomeForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Submit('submit','Importer',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.helper.form_method='POST'

class ImportAffectationForm(forms.Form):
    formation=forms.ModelChoiceField(queryset=Formation.objects.filter(annee_univ__encours=True).order_by('annee_univ__annee_univ','programme__ordre'))
    file=forms.FileField(label='Choisir un fichier', widget=forms.FileInput(attrs={'class':"custom-file-input"}))
    
    def __init__(self, *args, **kwargs):
        super(ImportAffectationForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.helper.add_input(Submit('submit','Importer',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.helper.form_method='POST'

class ImportDeliberationForm(forms.Form):
    def __init__(self, annee_univ_pk, *args, **kwargs):
        super(ImportDeliberationForm, self).__init__(*args, **kwargs)
        self.helper=FormHelper()
        self.fields['formation']=forms.ModelChoiceField(queryset=Formation.objects.filter(annee_univ__annee_univ=annee_univ_pk).order_by('annee_univ__annee_univ','programme__ordre'))
        self.fields['file']=forms.FileField(label='Choisir un fichier', widget=forms.FileInput(attrs={'class':"custom-file-input"}))
        self.helper.add_input(Submit('submit','Importer',css_class='btn-primary'))
        self.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.helper.form_method='POST'

class MatiereFormHelper(FormHelper):
    #form_method = 'GET'
    layout=Layout(
        TabHolder(
            Tab('Identification',
                Div(
                    'code', 'precision', css_class="row"
                ),
                Div(
                    'pfe', 'mode_projet', css_class="row"
                ),
                Div(
                    'coef', 'credit', css_class="row"
                ),
                Div(
                    'titre', 'titre_en', 'titre_a', css_class="row"
                ),

                Div(
                    'vh_cours', 'vh_td','edition', css_class="row"
                )
            ),
            Tab('Objectifs, Compétences et Pré-requis',
                'ddc', 'pre_requis', 'objectifs'
            ),
            Tab('Contenu',
                'contenu'
            ),
            Tab('Compléments',
                'travail_perso',
                'bibliographie'
            )
        ),
    )

class CreditForm(forms.Form):
    class Meta:
         model = Credit
         fields = ['chapitre', 'article', 'credit_allouee']
    chapitre = forms.ModelChoiceField(
        queryset=Chapitre.objects.all(),
        label=u"Credit",
        widget=ModelSelect2Widget(attrs={'style':'width:800px; height:10px;'},
            model=Credit,
            search_fields=['code_chap__icontains'],
            dependent_fields={'article': 'articles'},
        )
    )
    article = forms.ModelChoiceField(
        queryset=Article.objects.all(),
        label=u"Credit",
        widget=ModelSelect2Widget(
            model=Credit,
            search_fields=['code_art__icontains'],
            dependent_fields={'chapitre' : 'chapitre'},
            attrs={'style': 'width:800px; height:10px;'},
        )

    )
