import glob
import json
import os

from edc_utilities import edc_lineage
from metadata_utilities import check_schema
from metadata_utilities import generic_settings, generic
from metadata_utilities import messages
from metadata_utilities import mu_logging, json_file_utilities


class ConvertJSONtoEDCLineage:
    """
    Converts JSON file to a JSON payload that can be send to Informatica EDC using its APIs
    """
    code_version = "0.2.2"

    def __init__(self):
        self.json_file = "not provided"
        self.meta_type = "unknown"
        self.result = messages.message["undetermined"]
        self.settings = generic_settings.GenericSettings()
        self.generic = generic.Generic()
        self.json_directory = self.settings.json_directory
        self.target = self.settings.target
        self.overall_result = messages.message["ok"]
        self.mu_log = mu_logging.MULogging()
        # For Azure Monitor
        self.mu_log.code_version = self.code_version
        self.edc_lineage = edc_lineage.EDCLineage()
        self.json_file_utilities = json_file_utilities.JSONFileUtilities()
        self.data = ""

    def generate_file_structure(self):
        """
        Generate the metadata file for the data. The result is a file with only a header. No real data is needed.
        """
        module = "generate_file_structure"
        file_result = messages.message["ok"]
        with open(self.json_file) as entity:
            data = json.load(entity)
        if data["entity_type"] == "file":
            filename = data["name"]
            self.mu_log.log(self.mu_log.DEBUG, "entity type = file. Generating metafile for " + filename, module)
            entity_uuid = data["uid"]
            # find the entity_uuid in the property physical_entity of a physical_attribute file
            file_result = self.generic.find_json(entity_uuid, "physical_attribute", "physical_entity"
                                                 , log_prefix="find entity " + entity_uuid + " - ")
            attributes = self.generic.attribute_list
            if file_result["code"] == "OK":
                file_result = self.create_metafile(filename, attributes)
        else:
            self.mu_log.log(self.mu_log.DEBUG, "entity is not a file. Skipping metafile creation", module)
        return file_result

    def create_metafile(self, filename, attributes):
        """
        A metafile is created for Informatica EDC to scan. This way no real data is needed.
        """
        module = "create_metafile"
        self.mu_log.log(self.mu_log.DEBUG, "Start writing file", module)
        concatenated = self.generic.convert_list_into_string(attributes)
        if self.target == "local":
            file_result = self.generic.write_local_file(filename, concatenated)
        else:
            # TODO: Implement "azure_blob"
            self.mu_log.log(self.mu_log.DEBUG
                            , "In this release the only target is local. In the future Azure Blob will be added."
                            , module)
            file_result = messages.message["not_implemented"]

        self.mu_log.log(self.mu_log.DEBUG, "End writing file", module)
        return file_result

    def process_files(self):
        """
        Process files in the configued json directory (check config.json)
        For each file: Validate its schema and generate the metadata definition file or lineage file
            (depends on the meta_type of the file found)
        """
        module = "process_files"
        directory = self.settings.json_directory
        self.mu_log.log(self.mu_log.INFO, "===============================================", module)
        self.mu_log.log(self.mu_log.INFO, "Processing JSON files in directory " + directory, module)
        self.mu_log.log(self.mu_log.INFO, "===============================================", module)
        for file in glob.glob(directory + "*.json"):
            self.json_file = file
            base_filename = os.path.splitext(os.path.basename(self.json_file))[0]
            self.mu_log.area = base_filename
            self.mu_log.log(self.mu_log.INFO, "JSON file is: " + self.json_file, module)
            self.data = self.json_file_utilities.get_json(self.json_file)
            file_result = messages.message["ok"]
            check = check_schema.CheckSchema()
            check.mu_log.area = base_filename
            check_result = check.check_schema(self.data)
            if check_result["code"] == "OK":
                self.mu_log.log(self.mu_log.DEBUG, "schema check returned OK", module)
                self.meta_type = check.meta_type
                file_result = self.process_physical_entity_and_attribute()
                if file_result["code"] == "OK":
                    self.mu_log.log(self.mu_log.DEBUG, "file processed successfully", module)
                else:
                    self.overall_result = file_result
            else:
                self.overall_result = check_result
                self.mu_log.log(self.mu_log.DEBUG, "schema check failed with: " + check_result["code"] + " - "
                                + check_result["message"], module)
            self.mu_log.log(self.mu_log.INFO, "=== END ============================================", module)
        return self.overall_result

    def process_physical_entity_and_attribute(self):
        """
        Generate metadata files to be parsed by EDC
        """
        file_result = messages.message["ok"]
        module = "process_physical_entity_and_attribute"

        if self.meta_type not in ("physical_entity", "physical_entity_association", "physical_attribute_association"):
            self.mu_log.log(self.mu_log.DEBUG,
                            "file is not a physical entity or an association. File ignored."
                            , module)
            return file_result

        if self.meta_type == "physical_entity":
            file_result = self.generate_file_structure()
            return file_result

        if self.meta_type == "physical_attribute_association":
            file_result = self.generate_transformations()
            self.mu_log.log(self.mu_log.DEBUG, "The generation of transformation files returned >"
                            + file_result['code'] + "<"
                            , module)

        if self.meta_type in ("physical_attribute_association", "physical_entity_association"):
            file_result = self.process_lineage_request()
            self.mu_log.log(self.mu_log.DEBUG, "lineage processing completed with code >"
                            + file_result['code'] + "<"
                            , module)
        return file_result

    def generate_transformations(self):
        """
        generate a transformation file for each encountered transformation in the attribute_association json
        """
        module = "generate_transformations"
        overall_result = messages.message["undetermined"]
        if not "source_target_attribute_links" in self.data:
            self.mu_log.log(self.mu_log.DEBUG,
                            "did not find source_target_attribute_links. Transformation processing suppressed.", module)
            return messages.message["ok"]

        self.mu_log.log(self.mu_log.DEBUG, "found source_target_attribute_links", module)
        for link in self.data["source_target_attribute_links"]:
            self.mu_log.log(self.mu_log.DEBUG, "found transformation >" + link["transformation"]["uid"] + "<")
            source_attributes = link["transformation"]["from"]
            self.mu_log.log(self.mu_log.DEBUG, "# source attributes: " + str(len(source_attributes)))
            for source_attribute in source_attributes:
                self.mu_log.log(self.mu_log.VERBOSE, "source attribute: " + source_attribute)
            self.mu_log.log(self.mu_log.DEBUG, "target attribute: " + link["transformation"]["to"])
            self.mu_log.log(self.mu_log.VERBOSE, "description: " + link["description"])
            self.mu_log.log(self.mu_log.VERBOSE, "formula: " + link["formula"])

        return overall_result

    def process_lineage_request(self):
        # Generate the lineage file or payload
        module = "process_lineage_request"
        overall_result = messages.message["undetermined"]
        # TODO: generate json payload for the Metadata Interface APIs for lineage
        #       something like this:
        #           json_result = self.metadata_lake_lineage.generate_lineage("json_payload", self.meta_type, self.data)
        self.edc_lineage.mu_log.area = self.mu_log.area
        json_result = self.edc_lineage.generate_lineage("json_payload", self.meta_type, self.data)
        if json_result["code"] == "OK":
            # Send lineage info to metadata target
            send_result = self.send_metadata()
            self.mu_log.log(self.mu_log.DEBUG, "lineage creation completed with >" + send_result['code'] + "<", module)
            if send_result["code"] != "OK":
                overall_result = send_result
        else:
            overall_result = json_result
            self.mu_log.log(self.mu_log.ERROR, "json_payload lineage creation completed with >" + json_result['code']
                            + "<", module)

        return overall_result

    def send_metadata(self):
        module = "send_metadata"
        target = self.settings.metadata_store
        self.mu_log.log(self.mu_log.DEBUG, "sending lineage info to " + target, module)

        if target == "edc":
            send_result = self.edc_lineage.send_metadata_to_edc()
        elif target == "metadata_lake":
            send_result = self.send_metadata_to_metadata_lake()
        else:
            self.mu_log.log(self.mu_log.DEBUG, "unknown metadata target type: " + target, module)
            send_result = messages.message["unknown_metadata_target"]

        return send_result

    def send_metadata_to_metadata_lake(self):
        send_result = messages.message["not_implemented"]
        return send_result

    def main(self):
        module = "main"
        process_result = self.process_files()
        self.mu_log.log(self.mu_log.INFO, "Result: " + process_result["code"] + " - " + process_result["message"],
                        module)
        return process_result


if __name__ == "__main__":
    result = ConvertJSONtoEDCLineage().main()
