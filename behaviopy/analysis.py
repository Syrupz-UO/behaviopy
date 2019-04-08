import numpy as np
import pandas as pd
from scipy import special
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import matplotlib.cm as cm
import matplotlib.colors as colors
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
from statsmodels.sandbox.regression.predstd import wls_prediction_std

qualitative_colorset = ["#000000", "#E69F00", "#56B4E9", "#009E73","#F0E442", "#0072B2", "#D55E00", "#CC79A7"]

def behaviopy_style():
	from matplotlib import rcParams
	plt.style.use('ggplot')
	rcParams.update({
		'font.size':12,
		'figure.autolayout': True,
		'font.family':'sans-serif',
		'font.sans-serif':['Liberation Sans'],
		'xtick.labelsize':'medium',
		'ytick.labelsize':'medium',
		})

class MidpointNormalize(colors.Normalize):
	def __init__(self, vmin=None, vmax=None, midpoint=None, clip=False):
		self.midpoint = midpoint
		colors.Normalize.__init__(self, vmin, vmax, clip)

	def __call__(self, value, clip=None):
		# Ignoring masked values and all kinds of edge cases...
		x, y = [self.vmin, self.midpoint, self.vmax], [0, 0.5, 1]
		return np.ma.masked_array(np.interp(value, x, y))

def p_from_r(r,n):
	r = max(min(r, 1.0), -1.0)
	df = n-2
	if abs(r) == 1.0:
		prob = 0.0
	else:
		t_squared = r*r * (df / ((1.0 - r) * (1.0 + r)))
		prob = special.betainc(0.5*df, 0.5, df / (df + t_squared))
	return prob

def correlation_matrix(df_x_path,
	df_y_path=None,
	x_cols=None,
	y_cols=None,
	x_dict=None,
	y_dict=None,
	x_normalize=False,
	y_normalize=False,
	correction="fdr_bh",
	entries=None,
	er=0.05,
	output="pearson",
	save_as=None,
	xlabel_rotation="vertical",
	bp_style=True,
	):
	"""
	Highly parameterized correlation matrix of variables given by the columns of one or two dataframes.

	Parameters
	----------
	df_x_path : str
		Path to dataframe from which to select the columns as correlation matrix variables.
	df_y_path : str, optional
		Path to second dataframe from which to select the columns as correlation matrix variables.
	x_cols : list, optional
		Exclusive list of columns from `df_x_path` to use as correlation matrix variables.
	y_cols : list, optional
		Exclusive list of columns from `df_y_path` to use as correlation matrix variables.
	x_dict : dict, optional
		Dictionary based on which to rename the correlation matrix variables derived from `df_x_path` columns.
	y_dict : dict, optional
		Dictionary based on which to rename the correlation matrix variables derived from `df_y_path` columns.
	x_normalize : bool, optional
		Whether to normalize (divide by the mean) the rows from `df_x_path`.
	y_normalize : bool, optional
		Whether to normalize (divide by the mean) the rows from `df_y_path`.
	correction : str, optional
		Values from `statsmodels.stats.multitest.multitest_methods_names` specifying which mthod to use for multiple testing correction.
	entries : list, optional
		A list of values specifying which row indices from `df_x_path` and `df_y_path` to consider for the correlation matrix.
	er : float, optional
		Error rate (can be either FWER or FDR, depending on the value of `correction`) to use for the multiple testing correction.
	output : {"p", "pearsonr", "p_corrected", "slope"}
		Which correlation metric to display on the matrix.
	save_as : string, optional
		Path of output figure.
	xlabel_rotation : {"vertical", int}, optional
		How to rotate the x-axis labels.

	Returns
	-------
	dfc : pandas.DataFrame
		Pandas dataframe of the correlation matrix.
	"""
	if bp_style:
		behaviopy_style()

	if xlabel_rotation != "vertical":
		ha="left"
	else:
		ha="center"

	df = pd.read_csv(df_x_path, index_col=0)

	if not x_cols:
		x_cols = list(df.columns)

	if df_y_path:
		dfy = pd.read_csv(df_y_path, index_col=0)
		if not y_cols:
			y_cols = list(dfy.columns)
		df = pd.concat([df, dfy], axis=1)

	if entries:
		df = df.loc[entries]

	if x_normalize:
		df[x_cols] = df[x_cols].apply(lambda x: (x / x.mean()))
	if y_normalize:
		df[y_cols] = df[y_cols].apply(lambda x: (x / x.mean()))

	if output == "pearsonr":
		dfc = df.corr()
		cmap = cm.PiYG
		cbar_label = "Pearson's r"
	elif output == "slope":
		dfc = df.corr() * (df.std().values / df.std().values[:, np.newaxis])
		cmap = cm.PiYG
		cbar_label = "Slope"
	elif output == "p":
		n = len(df)
		dfc = df.corr()
		dfc = dfc.applymap(lambda x: p_from_r(x,n))
		cmap = cm.BuPu_r
		cbar_label = "p-value (uncorrected)"
	elif output == "p_corrected":
		n = len(df)
		dfc = df.corr()
		dfc = dfc.applymap(lambda x: p_from_r(x,n))
		dfc_corrected = multipletests(dfc.as_matrix().flatten(), er, correction)[1].reshape(np.shape(dfc))
		dfc = pd.DataFrame(dfc_corrected, dfc.index, dfc.columns)
		cmap = cm.BuPu_r
		if "fdr" in correction:
			cbar_label = "p-value (FDR={} corrected)".format(str(er))
		else:
			cbar_label = "p-value (FWER={} corrected)".format(str(er))

	dfc = dfc.loc[y_cols]
	dfc = dfc[x_cols]

	fig, ax = plt.subplots()
	if output not in ["p", "p_corrected"]:
		im = ax.matshow(dfc, norm=MidpointNormalize(midpoint=0.), cmap=cmap)
	else:
		im = ax.matshow(dfc, norm=MidpointNormalize(midpoint=0.05), cmap=cmap)
	if x_dict:
		plt.xticks(range(len(x_cols)), failsafe_apply_dict(x_cols, x_dict), rotation=xlabel_rotation, ha=ha)
	else:
		plt.xticks(range(len(x_cols)), x_cols, rotation=xlabel_rotation, ha=ha)
	if y_dict:
		plt.yticks(range(len(y_cols)), failsafe_apply_dict(y_cols, y_dict))
	else:
		plt.yticks(range(len(y_cols)), y_cols)
	ax.grid(False)
	ax.tick_params(axis="both",which="both",bottom="off",top="off",length=0)

	divider = make_axes_locatable(ax)
	cax = divider.append_axes("right", size="5%", pad=0.05)
	cbar = fig.colorbar(im, cax=cax, label=cbar_label)

	if save_as:
		plt.savefig(save_as,dpi=300, transparent=True)

	return dfc

def failsafe_apply_dict(mylist, dictionary):
	"""
	Translate the values in a list based upon a dictionary, if the respective values are keys in the dictionary - otherwise preserve the values.

	Parameters
	----------
	mylist : list
		A list of values.
	dictionary : dict
		A dictionary containing (some of) the values of `mylist` as keys.

	Returns
	-------
	list
		A list of translated values.
	"""
	#we create a new list, to not modify the old one in-place
	converted_list = []
	for ix, i in enumerate(mylist):
		try:
			converted_value = dictionary[i]
		except KeyError:
			continue
		else:
			converted_list.append(converted_value)
	return converted_list

def regression_and_scatter(df_x_path, x_name, y_names,
	df_y_path=None,
	roi_normalize=True,
	confidence_intervals=False,
	prediction_intervals=False,
	animals=None,
	):

	df = pd.read_csv(df_x_path, index_col=0)

	if df_y_path:
		dfy = pd.read_csv(df_y_path, index_col=0)
		df = pd.concat([df, dfy], axis=1)

	if animals:
		df = df.loc[animals]

	if roi_normalize:
		df[x_cols] = df[x_cols].apply(lambda x: (x / x.mean()))

	fig, ax = plt.subplots()
	ax.set_xmargin(0.1)
	ax.set_ymargin(0.11)
	df[x_cols] = df[x_cols].apply(lambda x: (x / x.mean()))

	fig, ax = plt.subplots()
	ax.set_xmargin(0.1)
	ax.set_ymargin(0.11)

	for ix, y_name in enumerate(y_names):
		x = df[[x_name]].values
		y = df[[y_name]].values

		x_ = sm.add_constant(x) # constant intercept term
		model = sm.OLS(y, x_)

	for ix, y_name in enumerate(y_names):
		x = df[[x_name]].values
		y = df[[y_name]].values

		x_ = sm.add_constant(x) # constant intercept term
		model = sm.OLS(y, x_)
		fitted = model.fit()
		x_pred = np.linspace(x.min(), x.max(), 50)
		x_pred2 = sm.add_constant(x_pred)
		y_pred = fitted.predict(x_pred2)

		y_hat = fitted.predict(x_)
		y_err = y - y_hat
		mean_x = x.mean()
		n = len(x)
		dof = n - fitted.df_model - 1
		t = stats.t.ppf(0.05, df=dof)
		s_err = np.sum(np.power(y_err, 2))

		if confidence_intervals:
			conf = t * np.sqrt((s_err/(n-2))*(1.0/n + (np.power((x_pred-mean_x),2) / ((np.sum(np.power(x_pred,2))) - n*(np.power(mean_x,2))))))
			upper_conf = y_pred + abs(conf)
			lower_conf = y_pred - abs(conf)
			ax.fill_between(x_pred, lower_conf, upper_conf, color=qualitative_colorset[ix], alpha=0.3)

		if prediction_intervals:
			sdev_pred, lower_pred, upper_pred = wls_prediction_std(fitted, exog=x_pred2, alpha=0.05)
			ax.fill_between(x_pred, lower_pred, upper_pred, color=qualitative_colorset[ix], alpha=0.08)

		data_points = ax.plot(x,y,'o',color=qualitative_colorset[ix],markeredgecolor=qualitative_colorset[ix])
		ax.tick_params(axis="both",which="both",bottom="off",top="off",length=0)
		ax.plot(x_pred, y_pred, '-', color=qualitative_colorset[ix], linewidth=2, label=y_name)
	plt.legend(loc="best")
