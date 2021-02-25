from django import forms
from django.db import models

# Create your models here.
from wagtail.core.models import Page
from wagtail.core.fields import RichTextField
from wagtail.admin.edit_handlers import FieldPanel

from modelcluster.fields import ParentalKey, ParentalManyToManyField
from modelcluster.contrib.taggit import ClusterTaggableManager
from taggit.models import TaggedItemBase

from wagtail.snippets.models import register_snippet

from wagtail.documents.models import Document
from wagtail.documents.edit_handlers import DocumentChooserPanel

@register_snippet
class InformationForActionCategory(models.Model):
    name = models.CharField(max_length=255)

    panels = [
        FieldPanel('name'),
    ]

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Information For Action Categories'



class InformationForActionPageTag(TaggedItemBase):
    content_object = ParentalKey(
        'InformationForActionPage',
        related_name='tagged_items',
        on_delete=models.CASCADE
    )


class InformationForActionPage(Page):
    date = models.DateField("Post date")
    intro = models.CharField(max_length=250)
    body = RichTextField(blank=True)
    tags = ClusterTaggableManager(through=InformationForActionPageTag, blank=True)
    categories = ParentalManyToManyField('resources.InformationForActionCategory', blank=True)
    author = models.CharField(max_length=250, default='None')
    pdf_file = models.ForeignKey(
        'wagtaildocs.Document',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )


    content_panels = Page.content_panels + [
        FieldPanel('date'),
        FieldPanel('author'),
        FieldPanel('intro'),
        FieldPanel('tags'),
        FieldPanel('categories', widget=forms.CheckboxSelectMultiple),
        FieldPanel('body', classname="full"),
        DocumentChooserPanel('pdf_file')
    ]

class IABIndexPage(Page):
    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro', classname="full")
    ]

class IABDemolitionsIndexPage(Page):
    intro = models.CharField(max_length=250)
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('body', classname="full")
    ]

class IABAffordabilityIndexPage(Page):
    intro = models.CharField(max_length=250)
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('body', classname="full")
    ]

class IABHousingIndexPage(Page):
    intro = models.CharField(max_length=250)
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('body', classname="full")
    ]

class IABForeclosuresIndexPage(Page):
    intro = models.CharField(max_length=250)
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('body', classname="full")
    ]

class InformationForActionTagIndexPage(Page):

    def get_context(self, request):

        # Filter by tag
        tag = request.GET.get('tag')
        informationforactionpages = InformationForActionPage.objects.filter(tags__name=tag)

        # Update template context
        context = super().get_context(request)
        context['informationforactionpages'] = informationforactionpages
        return context


class OfficialProgramReportsPage(Page):
    date = models.DateField("Post date")
    intro = models.CharField(max_length=250)
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('date'),
        FieldPanel('intro'),
        FieldPanel('body', classname="full"),
    ]

class HomePage(Page):
    intro = models.CharField(max_length=1000)
    geographic_area_text = models.CharField(max_length=1000)
    parcel_id_text = models.CharField(max_length=1000)
    info_for_action_top = RichTextField(blank=True)
    info_for_action_bottom = RichTextField(blank=True)
    whos_working_on_what = RichTextField(blank=True)
    detroit_housing_tools_header = RichTextField(blank=True)
    detroit_housing_tools = RichTextField(blank=True)
    national_housing_tools_header = RichTextField(blank=True)
    national_housing_tools = RichTextField(blank=True)
    other_resources = RichTextField(blank=True)
    footer_top = RichTextField(blank=True)
    footer_bottom = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('geographic_area_text'),
        FieldPanel('parcel_id_text', classname="full"),
        FieldPanel('info_for_action_top', classname="full"),
        FieldPanel('info_for_action_bottom', classname="full"),
        FieldPanel('whos_working_on_what', classname="full"),
        FieldPanel('detroit_housing_tools_header', classname="full"),
        FieldPanel('detroit_housing_tools', classname="full"),
        FieldPanel('national_housing_tools_header', classname="full"),
        FieldPanel('national_housing_tools', classname="full"),
        FieldPanel('other_resources', classname="full"),
        FieldPanel('footer_top', classname="full"),
        FieldPanel('footer_bottom', classname="full"),
    ]
