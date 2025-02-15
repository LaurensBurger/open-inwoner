import json
import re
from typing import Union

from django.contrib.gis.db.models import PointField
from django.core.exceptions import ValidationError
from django.db import connection, models
from django.utils.translation import ugettext_lazy as _

from geopy.exc import GeopyError
from localflavor.nl.models import NLZipCodeField

from open_inwoner.utils.geocode import geocode_address


class GeoModelQuerySet(models.QuerySet):
    def get_geojson_feature_collection(self) -> str:
        """
        Returns a geojson feature collection for all objects in this queryset.
        """
        return json.dumps(
            {
                "type": "FeatureCollection",
                "features": [o.get_geojson_feature(False) for o in self],
            }
        )

    def get_centroid(self) -> Union[dict, None]:
        """
        I apologize.

        This uses postgis to figure out the centroid of the objects in this queryset.
        """
        ids = self.values_list("id", flat=True)

        if not ids:
            return

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT ST_AsText(ST_Centroid(ST_Collect(geometry))) "
                "FROM pdc_productlocation "
                "WHERE id in %s",
                [tuple(ids)],
            )
            row = cursor.fetchone()

        try:
            point = row[0]
            m = re.findall(r"[0-9\.]+", point)
            return {
                "lng": m[0],
                "lat": m[1],
            }
        except IndexError:
            return


class GeoModel(models.Model):
    street = models.CharField(
        _("street"), blank=True, max_length=250, help_text=_("Address street")
    )
    housenumber = models.CharField(
        _("house number"),
        blank=True,
        max_length=250,
        help_text=_("Address house number"),
    )
    postcode = NLZipCodeField(_("postcode"), help_text=_("Address postcode"))
    city = models.CharField(_("city"), max_length=250, help_text=_("Address city"))
    geometry = PointField(
        _("geometry"),
        help_text=_("Geo coordinates of the location"),
    )

    objects = GeoModelQuerySet.as_manager()

    class Meta:
        abstract = True

    @property
    def address_str(self):
        return f"{self.address_line_1}, {self.address_line_2}"

    @property
    def address_line_1(self):
        return f"{self.street} {self.housenumber}"

    @property
    def address_line_2(self):
        # geocoding doesn't work if postcode has space inside
        postcode = self.postcode.replace(" ", "")
        return f"{postcode} {self.city}"

    def clean(self):
        super().clean()

        self.clean_geometry()

    def clean_geometry(self):
        model = self.__class__
        # # if address is not changed - do nothing
        if self.id and self.address_str == model.objects.get(id=self.id).address_str:
            return

        # locate geo coordinates using address string
        try:
            geometry = geocode_address(self.address_str)
        except GeopyError as exc:
            raise ValidationError(
                _("Locating geo coordinates has failed: %(exc)s") % {"exc": exc}
            )
        except IndexError:
            raise ValidationError(_("No location data was provided"))

        if not geometry:
            raise ValidationError(
                _(
                    "Geo coordinates of the address can't be found. "
                    "Make sure that the address data are correct"
                )
            )
        self.geometry = geometry

    def get_geojson_feature(self, stringify: bool = True) -> Union[str, dict]:
        """
        Returns a geojson feature for this object.
        If stringify equals `True` (default), a JSON string is returned, a dict otherwise.
        """
        feature = {
            "type": "Feature",
            "geometry": json.loads(self.get_geojson_geometry()),
            "properties": self.get_serialized_fields(),
        }

        if stringify:
            return json.dumps(feature)
        return feature

    def get_geojson_geometry(self) -> str:
        """
        Returns a geojson geometry for this object.
        """
        return str(self.geometry.geojson)

    def get_serialized_fields(self) -> dict:
        """
        Returns fields (and combination of fields via method) listed in serializable_fields (see below)
        as dict if JSON serializable.
        """
        serializable_fields = [
            "name",
            "address_line_1",
            "address_line_2",
            "email",
            "phonenumber",
        ]
        serialized_fields = {}

        for name in serializable_fields:
            try:
                value = getattr(self, name)
            except AttributeError:
                continue

            try:
                json.dumps(value)  # Check if json serializable.
                serialized_fields[name] = value
            except TypeError:
                continue

        return serialized_fields
