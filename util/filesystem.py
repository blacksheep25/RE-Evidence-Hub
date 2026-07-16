"""
filesystem.py

Filesystem helper functions.
"""


import os



class FileSystem(object):


    # --------------------------------------------------------
    # Ensure directory exists
    # --------------------------------------------------------

    @staticmethod
    def ensure_directory(
            path):


        if not os.path.exists(path):

            os.makedirs(path)



    # --------------------------------------------------------
    # Write text file
    # --------------------------------------------------------

    @staticmethod
    def write_text(
            path,
            content):


        directory = os.path.dirname(path)


        if directory and not os.path.exists(directory):

            os.makedirs(directory)



        with open(
            path,
            "w",
            encoding="utf-8",
            errors="replace"
        ) as f:

            f.write(
                content
            )



    # --------------------------------------------------------
    # Read text file
    # --------------------------------------------------------

    @staticmethod
    def read_text(
            path):


        with open(
            path,
            "r",
            encoding="utf-8",
            errors="replace"
        ) as f:


            return f.read()

    # --------------------------------------------------------
    # File exists
    # --------------------------------------------------------

    @staticmethod
    def exists(
            path):


        return os.path.exists(
            path
        )



    # --------------------------------------------------------
    # List files
    # --------------------------------------------------------

    @staticmethod
    def list_files(
            directory,
            extension=None):


        if not os.path.exists(directory):

            return []


        files = []


        for item in os.listdir(directory):


            if extension:


                if not item.endswith(
                    extension
                ):

                    continue


            files.append(item)


        return files
