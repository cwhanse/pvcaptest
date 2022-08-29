import pandas as pd
from captest.capdata import CapData

def load_das(self, path, filename, source=None, **kwargs):
    """
    Read measured solar data from a csv file.

    Utilizes pandas read_csv to import measure solar data from a csv file.
    Attempts a few diferent encodings, trys to determine the header end
    by looking for a date in the first column, and concantenates column
    headings to a single string.

    Parameters
    ----------
    path : str
        Path to file to import.
    filename : str
        Name of file to import.
    **kwargs
        Use to pass additional kwargs to pandas read_csv.

    Returns
    -------
    pandas dataframe
    """
    data = os.path.normpath(path + filename)

    encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
    for encoding in encodings:
        try:
            all_data = pd.read_csv(data, encoding=encoding, index_col=0,
                                   parse_dates=True, skip_blank_lines=True,
                                   low_memory=False, **kwargs)
        except UnicodeDecodeError:
            continue
        else:
            break

    if not isinstance(all_data.index[0], pd.Timestamp):
        for i, indice in enumerate(all_data.index):
            try:
                isinstance(dateutil.parser.parse(str(all_data.index[i])),
                           datetime.date)
                header_end = i + 1
                break
            except ValueError:
                continue

        if source == 'AlsoEnergy':
            header = 'infer'
        else:
            header = list(np.arange(header_end))

        for encoding in encodings:
            try:
                all_data = pd.read_csv(data, encoding=encoding,
                                       header=header, index_col=0,
                                       parse_dates=True,
                                       skip_blank_lines=True,
                                       low_memory=False, **kwargs)
            except UnicodeDecodeError:
                continue
            else:
                break

        if source == 'AlsoEnergy':
            row0 = all_data.iloc[0, :]
            row1 = all_data.iloc[1, :]
            row2 = all_data.iloc[2, :]

            row0_noparen = []
            for val in row0:
                if type(val) is str:
                    row0_noparen.append(val.split('(')[0].strip())
                else:
                    row0_noparen.append(val)

            row1_nocomm = []
            for val in row1:
                if type(val) is str:
                    strings = val.split(',')
                    if len(strings) == 1:
                        row1_nocomm.append(val)
                    else:
                        row1_nocomm.append(strings[-1].strip())
                else:
                    row1_nocomm.append(val)

            row2_noNan = []
            for val in row2:
                if val is pd.np.nan:
                    row2_noNan.append('')
                else:
                    row2_noNan.append(val)

            new_cols = []
            for one, two, three in zip(row0_noparen, row1_nocomm, row2_noNan):  # noqa: E501
                new_cols.append(str(one) + ' ' + str(two) + ', ' + str(three))  # noqa: E501

            all_data.columns = new_cols
            all_data = all_data.iloc[i:, :]
    all_data = all_data.apply(pd.to_numeric, errors='coerce')

    if source != 'AlsoEnergy':
        all_data.columns = [' '.join(col).strip() for col in all_data.columns.values]  # noqa: E501
    else:
        all_data.index = pd.to_datetime(all_data.index)

    return all_data

def load_pvsyst(self, path, filename, **kwargs):
    """
    Load data from a PVsyst energy production model.

    Parameters
    ----------
    path : str
        Path to file to import.
    filename : str
        Name of file to import.
    **kwargs
        Use to pass additional kwargs to pandas read_csv.

    Returns
    -------
    pandas dataframe
    """
    dirName = os.path.normpath(path + filename)

    encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
    for encoding in encodings:
        try:
            # pvraw = pd.read_csv(dirName, skiprows=10, encoding=encoding,
            #                     header=[0, 1], parse_dates=[0],
            #                     infer_datetime_format=True, **kwargs)
            pvraw = pd.read_csv(dirName, skiprows=10, encoding=encoding,
                                header=[0, 1], **kwargs)
        except UnicodeDecodeError:
            continue
        else:
            break

    pvraw.columns = pvraw.columns.droplevel(1)
    dates = pvraw.loc[:, 'date']
    try:
        dt_index = pd.to_datetime(dates, format='%m/%d/%y %H:%M')
    except ValueError:
        dt_index = pd.to_datetime(dates)
    pvraw.index = dt_index
    pvraw.drop('date', axis=1, inplace=True)
    pvraw = pvraw.rename(columns={"T Amb": "TAmb"})
    return pvraw

def load_data(self, path='./data/', fname=None, group_columns=True,
          column_type_report=True, source=None, load_pvsyst=False,
          clear_sky=False, loc=None, sys=None, **kwargs):
    """
    Import data from csv files.

    The intent of the default behavior is to combine csv files that have
    the same columns and rows of data from different times. For example,
    combining daily files of 5 minute measurements from the same sensors
    for each day.

    Use the path and fname arguments to specify a single file to import.

    Parameters
    ----------
    path : str, default './data/'
        Path to directory containing csv files to load.
    fname: str, default None
        Filename of specific file to load. If filename is none method will
        load all csv files into one dataframe.
    group_columns : bool, default True
        Generates translation dicitionary for column names after loading
        data.
    column_type_report : bool, default True
        If group_columns is true, then method prints summary of
        group_columns dictionary process including any possible data
        issues.  No effect on method when set to False.
    source : str, default None
        Default of None uses general approach that concatenates header
        data. Set to 'AlsoEnergy' to use column heading parsing specific to
        downloads from AlsoEnergy.
    load_pvsyst : bool, default False
        By default skips any csv file that has 'pvsyst' in the name.  Is
        not case sensitive.  Set to true to import a csv with 'pvsyst' in
        the name and skip all other files.
    clear_sky : bool, default False
        Set to true and provide loc and sys arguments to add columns of
        clear sky modeled poa and ghi to loaded data.
    loc : dict
        See the csky function for details on dictionary options.
    sys : dict
        See the csky function for details on dictionary options.
    **kwargs
        Will pass kwargs onto load_pvsyst or load_das, which will pass to
        Pandas.read_csv.  Useful to adjust the separator (Ex. sep=';').

    Returns
    -------
    None
    """
    if fname is None:
        files_to_read = []
        for file in os.listdir(path):
            if file.endswith('.csv'):
                files_to_read.append(file)
            elif file.endswith('.CSV'):
                files_to_read.append(file)

        all_sensors = pd.DataFrame()

        if not load_pvsyst:
            for filename in files_to_read:
                if filename.lower().find('pvsyst') != -1:
                    print("Skipped file: " + filename)
                    continue
                nextData = self.load_das(path, filename, source=source,
                                         **kwargs)
                all_sensors = pd.concat([all_sensors, nextData], axis=0)
                print("Read: " + filename)
        elif load_pvsyst:
            for filename in files_to_read:
                if filename.lower().find('pvsyst') == -1:
                    print("Skipped file: " + filename)
                    continue
                nextData = self.load_pvsyst(path, filename, **kwargs)
                all_sensors = pd.concat([all_sensors, nextData], axis=0)
                print("Read: " + filename)
    else:
        if not load_pvsyst:
            all_sensors = self.load_das(path, fname, source=source, **kwargs)  # noqa: E501
        elif load_pvsyst:
            all_sensors = self.load_pvsyst(path, fname, **kwargs)

    ix_ser = all_sensors.index.to_series()
    all_sensors['index'] = ix_ser.apply(lambda x: x.strftime('%m/%d/%Y %H %M'))  # noqa: E501
    self.data = all_sensors

    if not load_pvsyst:
        if clear_sky:
            if loc is None:
                warnings.warn('Must provide loc and sys dictionary\
                              when clear_sky is True.  Loc dict missing.')
            if sys is None:
                warnings.warn('Must provide loc and sys dictionary\
                              when clear_sky is True.  Sys dict missing.')
            self.data = csky(self.data, loc=loc, sys=sys, concat=True,
                             output='both')

    if group_columns:
        self.group_columns(column_type_report=column_type_report)

    self.data_filtered = self.data.copy()
